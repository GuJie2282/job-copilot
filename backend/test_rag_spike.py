"""
RAG 基建 spike（add-mock-interview 阶段 7.1 前置 de-risk）
==========================================================

验证三件事，全部通过才动手建 rag_service：
  1. numpy 可用（余弦相似度检索的依赖）
  2. 智谱 Embedding API 可调通（复用 LLM_API_KEY + LLM_BASE_URL，model=embedding-3）
  3. rank_bm25 可用（混合检索的关键词召回）

为什么不用 Chroma：chromadb 依赖 chroma-hnswlib，Windows 上要 MSVC 编译工具链，
对负责人（技术薄弱）不现实。面经库数据量极小（百级），numpy 余弦相似度足够，
且更透明、更好讲——「诚实的技术判断：不为用而用」（design.md 设计原则 3）。

作者：求职 Copilot 项目
日期：2026-07-20
"""

import os
from dotenv import load_dotenv

load_dotenv()


def check_numpy():
    """1. numpy 可用 + 余弦相似度算得对。"""
    import numpy as np
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 1.0, 0.0])
    cos = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
    assert abs(cos - 0.7071) < 0.001, f"余弦相似度算错：{cos}"
    return np


def check_embedding():
    """2. 智谱 embedding-3 可调通，返回合理维度。"""
    from langchain_openai import OpenAIEmbeddings
    emb = OpenAIEmbeddings(
        model="embedding-3",
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
    )
    # 两句语义相关的面试题 + 一句无关的
    texts = [
        "讲一次你 push 团队达成目标的经历",           # 行为面
        "请举一个你主动推动项目、带领团队的真实案例",  # 同义（行为面）
        "请用 SQL 写一个左连接",                      # 完全无关（技术）
    ]
    vecs = emb.embed_documents(texts)
    import numpy as np
    v = [np.array(x) for x in vecs]

    def cos(a, b):
        return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

    sim_same = cos(v[0], v[1])      # 同义题应高度相似
    sim_diff = cos(v[0], v[2])      # 无关题应较低
    return len(vecs[0]), sim_same, sim_diff


def check_bm25():
    """3. rank_bm25 可用。"""
    from rank_bm25 import BM25Okapi
    corpus = [["产品", "经理", "面试"], ["sql", "左连接"], ["项目", "经历"]]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(["产品", "经历"])
    return scores


def run():
    print("=" * 60)
    print("RAG 基建 spike：numpy / 智谱 embedding / rank_bm25")
    print("=" * 60)

    # 1. numpy
    np = check_numpy()
    print("[✓ PASS] numpy 可用，余弦相似度计算正确")

    # 2. 智谱 embedding
    try:
        dim, sim_same, sim_diff = check_embedding()
        ok_emb = sim_same > sim_diff        # 同义 > 无关
        print(f"[{'✓ PASS' if ok_emb else '✗ FAIL'}] 智谱 embedding-3：维度={dim}，"
              f"同义相似度={sim_same:.3f}，无关相似度={sim_diff:.3f}")
        if not ok_emb:
            print("         ⚠ 同义题相似度未高于无关题，embedding 语义性异常")
    except Exception as e:
        print(f"[✗ FAIL] 智谱 embedding 调用失败：{type(e).__name__}: {e}")
        print("         （排查：model 名、base_url、api_key、网络）")

    # 3. rank_bm25
    try:
        scores = check_bm25()
        ok_bm = scores[0] > scores[1]      # "产品经历" 应匹配第 0 篇 > 第 1 篇
        print(f"[{'✓ PASS' if ok_bm else '✗ FAIL'}] rank_bm25 可用：scores={scores.round(3).tolist()}")
    except Exception as e:
        print(f"[✗ FAIL] rank_bm25 失败：{type(e).__name__}: {e}")

    print("=" * 60)


if __name__ == "__main__":
    run()
