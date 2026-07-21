"""
RAG 基建服务（rag_service）
============================

面经库的「嵌入 + 混合检索」底层引擎。被 knowledge_service（个人库/公司库）调用，
本身不碰具体存储——存储由 knowledge_service 负责，本服务只做：
  1. 嵌入：文本 → 向量（智谱 embedding-3，复用 LLM_API_KEY/LLM_BASE_URL）
  2. 混合检索：向量语义 + BM25 关键词 + 来源优先级 三路融合排序

【诚实的技术判断：为什么不用 Chroma】
design.md 原定 Chroma + BGE。实际落地时发现：
  - chromadb 依赖 chroma-hnswlib，Windows 上要 MSVC C++ 编译工具链，对负责人不现实；
  - 本地 BGE 同样要下载约 100MB 权重。
而面经库数据量极小（个人库每用户几十~几百条，公司库种子每岗 10-20 条）——
为这点数据硬上需要编译的向量库是过度设计。改用：
  - 智谱 embedding API（复用现有 key，零下载）
  - SQLite 存 embedding（JSON 列）+ numpy 余弦相似度检索
  - rank_bm25 做关键词兜底
零额外重依赖、完全透明、毫秒级检索、更好讲——「不为用而用」（design 原则 3）。
数据飞轮的壁垒来自数据私有 + 飞轮闭环，与用什么向量库无关。

混合检索公式（对应 spec「混合检索」需求）：
  score = ( α · 向量余弦相似度 + (1-α) · BM25归一化分 ) × 来源优先级权重
  - 向量路：语义召回（同义题、换说法的题）
  - BM25 路：专业术语/岗位关键词精确命中（向量易漏的硬词）
  - 来源权重：curated > personal > ugc > llm_generated（spec 检索优先级）

作者：求职 Copilot 项目
日期：2026-07-20
"""

import os
import logging
from typing import List, Dict, Any, Optional

import numpy as np
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


# ============================================================================
# 1. 嵌入模型（智谱 embedding-3 单例）
# ============================================================================

# embedding-3 默认输出 2048 维（spike 实测：长文本语义区分度优于 embedding-2）
EMBEDDING_MODEL = "embedding-3"
EMBEDDING_DIM = 2048

_embeddings = None  # 单例缓存（OpenAIEmbeddings 实例）


def get_embeddings():
    """
    获取智谱 embedding 客户端（单例）。复用 LLM 配置（同一 key、同一 base_url）。
    智谱 embedding 接口是 OpenAI 兼容的 /embeddings，可直接用 langchain_openai。
    """
    global _embeddings
    if _embeddings is None:
        from langchain_openai import OpenAIEmbeddings
        _embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=os.getenv("LLM_BASE_URL"),
            api_key=os.getenv("LLM_API_KEY"),
        )
    return _embeddings


def embed_text(text: str) -> Optional[np.ndarray]:
    """
    单条文本 → 向量（float32 numpy 数组）。失败返回 None（上层降级为仅 BM25 检索）。

    用 None 而非抛异常：embedding 是「锦上添花」，挂了不应阻断检索——BM25 兜底。
    """
    if not text or not text.strip():
        return None
    try:
        vec = get_embeddings().embed_query(text)
        return np.asarray(vec, dtype=np.float32)
    except Exception as e:
        logger.warning(f"embedding 失败，降级为仅 BM25：{type(e).__name__}: {e}")
        return None


def embed_texts(texts: List[str]) -> List[Optional[np.ndarray]]:
    """批量嵌入。单条失败不影响其他条（对应位置返回 None）。"""
    if not texts:
        return []
    try:
        vecs = get_embeddings().embed_documents(texts)
        return [np.asarray(v, dtype=np.float32) for v in vecs]
    except Exception as e:
        logger.warning(f"批量 embedding 失败，逐条重试：{type(e).__name__}: {e}")
        return [embed_text(t) for t in texts]


# ============================================================================
# 2. 来源优先级（spec 检索优先级：curated > ugc > llm_generated）
# ============================================================================

def get_source_priority() -> Dict[str, float]:
    """
    来源 → 优先级权重（0-1）。检索排序时作为乘数。
    - curated（精选种子）：质量最高，演示用 → 1.0
    - personal（个人历史）：出题复练用，高 → 0.95
    - ugc（用户贡献）：真实面经，次高 → 0.85
    - llm_generated / llm_gen（AI 拟题）：质量打折 → 0.70
    """
    return {
        "curated": 1.00,
        "personal": 0.95,
        "ugc": 0.85,
        "llm_generated": 0.70,
        "llm_gen": 0.70,   # 兼容 question_generator 的标记
    }


# ============================================================================
# 3. 混合检索（向量语义 + BM25 关键词 + 来源优先级）
# ============================================================================

def _cosine(query_vec: np.ndarray, candidate_vec) -> float:
    """两个向量的余弦相似度。任一缺失返回 0。"""
    if query_vec is None or candidate_vec is None:
        return 0.0
    try:
        a = np.asarray(query_vec, dtype=np.float32)
        b = np.asarray(candidate_vec, dtype=np.float32)
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(a @ b / (na * nb))
    except Exception:
        return 0.0


def _tokenize_zh(text: str) -> List[str]:
    """
    中文分词（BM25 用）。MVP 不引 jieba，用「字符级 + 关键词双路」：
      - 单字序列：中文单字也有区分度，且覆盖所有词；
      - 这种粗分词对面经这种短文本足够，必要时再升级 jieba。
    """
    if not text:
        return []
    # 去空白与标点，按字符切
    return [ch for ch in text if ch.strip()]


def hybrid_search(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 5,
    alpha: float = 0.6,
    source_priority: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    混合检索：向量语义 + BM25 关键词 + 来源优先级 三路融合，返回 top_k。

    Args:
        query:            检索查询文本（如「产品经理 行为面 团队推动」）
        candidates:       候选条目列表，每个 dict 至少含 {text, source}，
                          可选 {vector}（已算好的 embedding，没有则只靠 BM25）
        top_k:            返回条数
        alpha:            向量权重（1-alpha 给 BM25）。默认 0.6 偏语义。
        source_priority:  来源优先级权重字典，默认 get_source_priority()

    Returns:
        排序后的 top_k 条，每个原条目附三个调试字段：
          _score（融合总分）、_vec_sim（向量相似度 0-1）、_bm25（BM25 归一化分 0-1）
    """
    if not candidates:
        return []

    source_priority = source_priority or get_source_priority()
    n = len(candidates)

    # ---- 路径 A：向量语义相似度 ----
    qv = embed_text(query)
    vec_raw = [0.0] * n
    if qv is not None:
        for i, c in enumerate(candidates):
            vec_raw[i] = _cosine(qv, c.get("vector"))
    # cosine ∈ [-1,1]，截断到 [0,1]（负相关当 0 处理）
    vec_norm = [max(0.0, min(1.0, s)) for s in vec_raw]

    # ---- 路径 B：BM25 关键词匹配 ----
    texts = [c.get("text", "") for c in candidates]
    tokenized = [_tokenize_zh(t) for t in texts]
    try:
        bm25 = BM25Okapi(tokenized)
        bm_raw = bm25.get_scores(_tokenize_zh(query))
    except Exception as e:
        logger.warning(f"BM25 失败，仅用向量路：{e}")
        bm_raw = np.zeros(n)
    bm_max = float(np.max(bm_raw)) if len(bm_raw) else 0.0
    bm_norm = [float(s / bm_max) if bm_max > 0 else 0.0 for s in bm_raw]

    # ---- 融合 + 来源优先级 ----
    results = []
    for i, c in enumerate(candidates):
        src = c.get("source", "llm_generated")
        src_w = source_priority.get(src, 0.70)
        score = (alpha * vec_norm[i] + (1 - alpha) * bm_norm[i]) * src_w
        r = dict(c)
        r["_score"] = round(score, 4)
        r["_vec_sim"] = round(vec_norm[i], 4)
        r["_bm25"] = round(bm_norm[i], 4)
        results.append(r)

    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:top_k]


# ============================================================================
# 主函数（自检用）
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("rag_service 自检：嵌入 + 混合检索")
    print("=" * 60)

    # 模拟公司库候选（含 vector 的走双路，不含的只靠 BM25）
    cands = [
        {"text": "行为面：讲一次你推动团队达成目标的经历，重点说数据结果。", "source": "curated"},
        {"text": "技术面：写一个 SQL 左连接，分析业务漏斗。", "source": "llm_generated"},
        {"text": "动机面：为什么想做产品经理？", "source": "ugc"},
    ]
    # 给前两条补 embedding（模拟已入库），第三条不补（验证 BM25 兜底）
    cands[0]["vector"] = embed_text(cands[0]["text"]).tolist() if embed_text(cands[0]["text"]) is not None else None
    cands[1]["vector"] = embed_text(cands[1]["text"]).tolist() if embed_text(cands[1]["text"]) is not None else None

    q = "团队推动的经历 数据结果"
    print(f"\n查询：{q}")
    for r in hybrid_search(q, cands, top_k=3):
        print(f"  [{r['_score']}] vec={r['_vec_sim']} bm25={r['_bm25']} src={r['source']}")
        print(f"     {r['text'][:40]}")
