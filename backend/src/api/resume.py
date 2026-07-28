"""
简历解析 API 路由

功能：
1. 文件上传解析（POST /api/resume/parse-file）
2. 文本粘贴解析（POST /api/resume/parse-text）
3. LLM 提取（POST /api/resume/extract）
4. 画像更新（POST /api/resume/update-profile）
5. 获取画像（GET /api/resume/profile）
6. 导出画像（GET /api/resume/export-profile）
7. 删除画像（DELETE /api/resume/profile）
8. 获取示例简历（GET /api/resume/sample-resumes）

作者：求职 Copilot 项目
日期：2026-07-03
"""

import os
import uuid
import tempfile
import json
import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# 导入服务
from src.services.resume_parser import parse_resume, deduplicate_text, extract_pdf_avatar, extract_docx_avatar
from src.services.quality_checker import check_text_quality, calculate_profile_confidence
from src.services.llm_retry import invoke_llm_with_retry, is_retryable
from src.services.profile_service import (
    save_profile,
    get_profile as get_profile_service,
    get_profile_confidence,
    delete_profile as delete_profile_service,
)
from src.core.deps import get_db
from src.models.profile import UserProfileModel
from src.graph.config import get_structured_llm, get_llm, UserProfile
from src.graph.prompts import get_extraction_prompt, get_section_extraction_prompt
from src.core.sse import (
    sse,
    sse_keepalive,
    STAGE,
    SEGMENT,
    REASONING,
    DONE,
    ERROR,
    STREAM_HEADERS,
    STREAM_MEDIA_TYPE,
)
from src.services.profile_extractor import (
    _extract_json_loose,
    _merge_sections,
    SECTION_ORDER,
    SECTION_LABEL,
    _SECTION_DEFAULT,
)
from src.services.llm_reasoning import stream_chat_with_reasoning


# ============================================================================
# 创建路由器
# ============================================================================

resume_router = APIRouter()


# ============================================================================
# 临时文件配置
# ============================================================================

# 临时文件目录
UPLOAD_DIR = tempfile.gettempdir()
RESUME_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "resume_uploads")

# 确保目录存在
os.makedirs(RESUME_UPLOAD_DIR, exist_ok=True)

# 文件大小限制（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024


# ============================================================================
# Pydantic 模型（请求和响应）
# ============================================================================

class ParseTextRequest(BaseModel):
    """文本粘贴解析请求"""
    text: str = Field(..., description="简历文本", min_length=50)
    user_id: Optional[str] = Field(None, description="用户 ID")


class UpdateProfileRequest(BaseModel):
    """更新画像请求"""
    user_id: Optional[str] = Field(None, description="用户 ID")
    profile: Dict[str, Any] = Field(..., description="个人画像数据")


class ExtractRequest(BaseModel):
    """LLM 提取请求"""
    text: str = Field(..., description="简历文本")
    quality_score: float = Field(1.0, description="文本质量分数", ge=0.0, le=1.0)
    is_retry: bool = Field(False, description="是否是重试")


class APIResponse(BaseModel):
    """通用 API 响应"""
    status: str = Field(..., description="状态：success, warning, error")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


class ParseResponse(APIResponse):
    """解析响应"""
    quality_score: Optional[float] = Field(None, description="质量分数")
    warnings: Optional[list[str]] = Field(None, description="警告列表")
    profile: Optional[Dict[str, Any]] = Field(None, description="个人画像")
    confidence: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="置信度")


# ============================================================================
# 画像提取（带重试的内部 helper）
# ============================================================================

def _extract_profile_with_retry(text: str, quality_score: float, max_retries: int = 2):
    """
    带重试的画像提取：同时处理「LLM API 异常」和「JSON 解析失败」两类常见失败。

    每次尝试：构建 prompt → 调用 LLM → 解析 JSON → Pydantic 校验。
    任一步失败都按指数退避重试；重试耗尽则抛出最后一次异常。

    为什么要重试 JSON 解析失败：智谱/DeepSeek 等 LLM 偶发会返回非合法 JSON
    （比如多余的文字、被截断），换一次调用通常就好了。

    Args:
        text: 简历文本
        quality_score: 文本质量分
        max_retries: 最大重试次数（默认 2，即最多 3 次尝试）

    Returns:
        profile: 结构化画像字典（已通过 UserProfile 校验）

    Raises:
        最后一次异常（所有重试失败后）
    """
    import time
    import logging
    from src.services.profile_extractor import extract_profile_sectioned

    logger = logging.getLogger(__name__)
    last_error = None

    # 分段提取（basic/education/work/project/skills 各一段）：段级容错 + 嵌套结构，
    # 替代旧的单次扁平提取（治超时 + 治字段错位）。详见 profile_extractor。
    for attempt in range(max_retries + 1):
        try:
            profile_dict = extract_profile_sectioned(text, quality_score)
            # Pydantic 校验（嵌套 UserProfile）
            profile = UserProfile(**profile_dict).model_dump()
            return profile
        except Exception as e:
            last_error = e
            # 不可重试错误（认证、参数等）→ 立即抛出
            if not is_retryable(e):
                raise
            if attempt < max_retries:
                delay = 1.0 * (2 ** attempt)  # 1s → 2s → 4s
                logger.warning(
                    f"画像提取失败（第 {attempt + 1}/{max_retries + 1} 次），"
                    f"{delay:.1f}s 后重试：{type(e).__name__}: {e}"
                )
                time.sleep(delay)

    logger.error(f"画像提取重试 {max_retries} 次仍失败，放弃。最后错误：{last_error}")
    raise last_error


# ============================================================================
# API 1: 文件上传解析（POST /api/resume/parse-file）
# ============================================================================

@resume_router.post("/parse-file", response_model=ParseResponse)
async def parse_resume_file(
    file: UploadFile = File(..., description="简历文件（PDF 或 Word）"),
    user_id: Optional[str] = Query(None, description="用户 ID")
):
    """
    上传并解析简历文件

    Args:
        file: 简历文件（PDF 或 Word）
        user_id: 用户 ID（可选）

    Returns:
        ParseResponse: 解析结果

    流程：
    1. 验证文件格式和大小
    2. 保存临时文件（使用 UUID 避免冲突）
    3. 解析文件（PDF/Word）
    4. 质量检测
    5. LLM 提取画像
    6. 计算置信度
    7. 返回结果
    """
    try:
        # 1. 验证文件格式
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.pdf', '.docx']:
            return ParseResponse(
                status="error",
                message=f"不支持的文件格式：{file_ext}。仅支持 PDF 和 Word 文档。",
                data=None
            )

        # 2. 读取文件内容并验证大小
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            return ParseResponse(
                status="error",
                message=f"文件过大（{file_size / 1024 / 1024:.2f}MB），最大支持 10MB。",
                data=None
            )

        # 3. 保存临时文件（使用 UUID 避免并发冲突）
        file_id = str(uuid.uuid4())
        file_path = os.path.join(RESUME_UPLOAD_DIR, f"{file_id}{file_ext}")

        with open(file_path, 'wb') as f:
            f.write(content)

        # 4. 解析文件
        result, error = parse_resume(file_path)

        # 4.5 提取头像（add-resume-avatar）：删临时文件前按文件类型提图；
        # 几何启发式选首页最像证件照的图，失败/无图降级跳过，不阻塞解析。
        avatar_url = None
        if user_id and not error:
            try:
                avatar_bytes_ext = None
                if file_ext == '.pdf':
                    avatar_bytes_ext = extract_pdf_avatar(file_path)
                elif file_ext == '.docx':
                    avatar_bytes_ext = extract_docx_avatar(file_path)
                if avatar_bytes_ext:
                    a_bytes, a_ext = avatar_bytes_ext
                    os.makedirs(AVATAR_DIR, exist_ok=True)
                    a_path = os.path.join(AVATAR_DIR, f"{user_id}.{a_ext}")
                    with open(a_path, "wb") as af:
                        af.write(a_bytes)
                    avatar_url = f"/static/avatars/{user_id}.{a_ext}"
            except Exception as ae:
                print(f"[WARNING] avatar extraction failed: {ae}")

        # 清理临时文件
        try:
            os.remove(file_path)
        except:
            pass

        # 5. 处理解析错误
        if error:
            return ParseResponse(
                status="error",
                message=error,
                data=None
            )

        # 6. 获取提取的文本
        text = result.get('text', '')

        # 7. 质量检测
        quality_score, warnings = check_text_quality(text)

        # 8. LLM 提取画像（带重试：处理 API 异常 + JSON 解析失败）
        try:
            profile = _extract_profile_with_retry(text, quality_score)

            # 注入解析提取到的头像 URL（若有）——前端拿到 profile 后随 update-profile 落库
            if avatar_url:
                profile["avatar_url"] = avatar_url

            # 9. 计算置信度
            confidence = calculate_profile_confidence(profile, text)

            # 10. 判断状态
            status = "success" if quality_score >= 0.8 else "warning"
            message = "简历解析成功" if quality_score >= 0.8 else "解析成功，但文本质量较低，请检查提取结果"

            return ParseResponse(
                status=status,
                message=message,
                data={
                    "text": text,
                    "parser": result.get("parser"),
                    "file_size": file_size,
                    "text_length": len(text)
                },
                quality_score=quality_score,
                warnings=warnings if quality_score < 0.8 else None,
                profile=profile,
                confidence=confidence
            )

        except Exception as e:
            return ParseResponse(
                status="error",
                message=f"LLM 提取失败：{str(e)}",
                data={
                    "text": text,
                    "quality_score": quality_score
                }
            )

    except Exception as e:
        return ParseResponse(
            status="error",
            message=f"文件上传解析失败：{str(e)}",
            data=None
        )


# ============================================================================
# API 2: 文本粘贴解析（POST /api/resume/parse-text）
# ============================================================================

@resume_router.post("/parse-text", response_model=ParseResponse)
async def parse_resume_text(request: ParseTextRequest):
    """
    解析粘贴的简历文本

    Args:
        request: 包含简历文本的请求

    Returns:
        ParseResponse: 解析结果

    流程：
    1. 验证文本长度
    2. 质量检测
    3. LLM 提取画像
    4. 计算置信度
    5. 返回结果
    """
    try:
        text = request.text

        # 0. 文本去重（粘贴的文本也可能含重复段落，与文件解析保持一致）
        text = deduplicate_text(text)

        # 1. 验证文本长度
        if len(text.strip()) < 50:
            return ParseResponse(
                status="error",
                message="文本过短，请提供完整的简历文本（至少 50 字符）。",
                data=None
            )

        # 2. 质量检测
        quality_score, warnings = check_text_quality(text)

        # 3. LLM 提取画像（带重试：处理 API 异常 + JSON 解析失败）
        try:
            profile = _extract_profile_with_retry(text, quality_score)

            # 4. 计算置信度
            confidence = calculate_profile_confidence(profile, text)

            # 5. 判断状态
            status = "success" if quality_score >= 0.8 else "warning"
            message = "文本解析成功" if quality_score >= 0.8 else "解析成功，但文本质量较低，请检查提取结果"

            return ParseResponse(
                status=status,
                message=message,
                data={
                    "text": text,
                    "text_length": len(text),
                    "source": "text"
                },
                quality_score=quality_score,
                warnings=warnings if quality_score < 0.8 else None,
                profile=profile,
                confidence=confidence
            )

        except Exception as e:
            return ParseResponse(
                status="error",
                message=f"LLM 提取失败：{str(e)}",
                data={
                    "text": text,
                    "quality_score": quality_score
                }
            )

    except Exception as e:
        return ParseResponse(
            status="error",
            message=f"文本解析失败：{str(e)}",
            data=None
        )


# ============================================================================
# API 2.5: 文本流式解析（POST /api/resume/parse-stream）—— SSE 分段提取
# ============================================================================

class ParseStreamRequest(BaseModel):
    """文本流式解析请求"""
    text: str = Field(..., description="简历文本", min_length=50)
    user_id: Optional[str] = Field(None, description="用户 ID")


@resume_router.post("/parse-stream")
async def parse_resume_text_stream(request: ParseStreamRequest):
    """
    文本流式解析（SSE 分段提取，对应 change add-streaming-pipeline 决策 5/6）：
    去重 → 质检 → 逐段 LLM 提取（basic/education/work/project/skills）。

    每段完成发 segment 事件（画像逐段成型），全部完成发 done；失败发 error。
    段内用 llm.astream 增量产出（连接持续活跃），并每若干 token 下发心跳保活。

    事件流（text/event-stream）：
      event: stage    —— 阶段进度 {message, node?}
      event: segment  —— 分段结果 {section, data}
      event: done     —— 完成 {status, quality_score, profile, confidence, text, warnings?}
      event: error    —— 失败 {error_code, error_message}
    """
    _logger = logging.getLogger(__name__)

    async def event_stream():
        try:
            text = deduplicate_text(request.text or "")
            if len(text.strip()) < 50:
                yield sse(ERROR, {
                    "error_code": "TEXT_TOO_SHORT",
                    "error_message": "文本过短，请提供完整的简历文本（至少 50 字符）。",
                })
                return

            yield sse(STAGE, {"message": "文本质量检测…"})
            quality_score, warnings = check_text_quality(text)

            # 分段提取（glm-4.5 reasoning）：每段独立 stream_chat_with_reasoning
            # —— reasoning 发思考事件（前端思考区），content 收集后整段解析为 segment
            partial: Dict[str, Any] = {}
            for section in SECTION_ORDER:
                yield sse(STAGE, {"message": SECTION_LABEL[section], "node": section})
                prompt = get_section_extraction_prompt(text, section)
                content_parts: list = []
                async for kind, delta in stream_chat_with_reasoning(prompt, temperature=0.0, timeout=120.0):
                    if kind == "reasoning":
                        yield sse(REASONING, {"delta": delta})
                    else:
                        content_parts.append(delta)
                data = _extract_json_loose("".join(content_parts))
                if data is None:
                    data = json.loads(json.dumps(_SECTION_DEFAULT[section]))  # 深拷贝默认值，容错
                if section == "basic" and isinstance(data, dict):
                    for k in _SECTION_DEFAULT["basic"]:
                        data.setdefault(k, None)
                partial[section] = data
                yield sse(SEGMENT, {"section": section, "data": data})

            profile = _merge_sections(partial)
            confidence = calculate_profile_confidence(profile, text)
            status = "success" if quality_score >= 0.8 else "warning"
            yield sse(DONE, {
                "status": status,
                "quality_score": quality_score,
                "warnings": warnings if quality_score < 0.8 else None,
                "text": text,
                "profile": profile,
                "confidence": confidence,
            })
        except Exception as e:
            _logger.exception("parse-stream 流式解析异常")
            yield sse(ERROR, {
                "error_code": "PARSE_FAILED",
                "error_message": f"解析失败：{e}",
            })

    return StreamingResponse(
        event_stream(),
        media_type=STREAM_MEDIA_TYPE,
        headers=STREAM_HEADERS,
    )


# ============================================================================
# API 3: LLM 提取（POST /api/resume/extract）
# ============================================================================

@resume_router.post("/extract")
async def extract_profile(request: ExtractRequest):
    """
    使用 LLM 从文本中提取画像（独立接口）

    Args:
        request: 包含文本和配置的请求

    Returns:
        APIResponse: 提取结果
    """
    try:
        text = request.text
        quality_score = request.quality_score
        is_retry = request.is_retry

        # LLM 提取
        llm = get_structured_llm(schema=UserProfile, temperature=0.0, tier="strong")  # 简历解析：主力档
        prompt = get_extraction_prompt(text, quality_score, is_retry)
        profile_obj = invoke_llm_with_retry(llm, prompt)
        profile = profile_obj.model_dump()

        return APIResponse(
            status="success",
            message=f"{'重试提取' if is_retry else '提取'}成功",
            data={
                "profile": profile,
                "mode": "retry" if is_retry else "standard"
            }
        )

    except Exception as e:
        return APIResponse(
            status="error",
            message=f"LLM 提取失败：{str(e)}",
            data=None
        )


# ============================================================================
# API 4: 更新画像（POST /api/resume/update-profile）
# ============================================================================

@resume_router.post("/update-profile")
async def update_profile(
    request: UpdateProfileRequest,
    db: Session = Depends(get_db)
):
    """
    更新个人画像（持久化到数据库，upsert：首次插入 / 已存在则覆盖）

    用户在简历解析后确认画像，前端调用本接口落库。
    """
    try:
        user_id = request.user_id
        if not user_id:
            return APIResponse(status="error", message="缺少 user_id", data=None)

        # 真正持久化（区块一：画像持久化落地）
        save_profile(db, user_id, request.profile)

        return APIResponse(
            status="success",
            message="画像已保存",
            data={
                "user_id": user_id,
                "updated_fields": list(request.profile.keys())
            }
        )

    except Exception as e:
        return APIResponse(
            status="error",
            message=f"画像保存失败：{str(e)}",
            data=None
        )


# ============================================================================
# API 4.5: 头像上传（POST /api/resume/avatar）— add-resume-avatar
# ============================================================================

# 头像存储目录（与 main.py 的 StaticFiles mount 一致：backend/data/avatars）
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVATAR_DIR = os.path.join(_BACKEND_ROOT, "data", "avatars")
AVATAR_MAX_SIZE = 2 * 1024 * 1024  # 2MB（不引入 Pillow 做压缩，靠上传大小限制；压缩留后续）


def _check_image_magic(data: bytes) -> Optional[str]:
    """根据文件头魔数判断图片类型，返回扩展名（jpg/png）；不合法返回 None。
    不只看扩展名/Content-Type，防止伪装的可执行文件上传。"""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return None


@resume_router.post("/avatar")
async def upload_avatar(
    user_id: str = Query(..., description="用户 ID"),
    file: UploadFile = File(..., description="头像图片（jpeg/png，≤2MB）"),
    db: Session = Depends(get_db),
):
    """
    上传用户头像（存文件系统 + URL 入库）。

    直接写 user_profiles.avatar_url——不走 save_profile，否则会整体覆盖 detail_json 丢画像明细。
    """
    data = await file.read()
    if len(data) > AVATAR_MAX_SIZE:
        return APIResponse(status="error", message="头像过大（≤ 2MB）", data={"error_code": "TOO_LARGE"})
    ext = _check_image_magic(data)
    if not ext:
        return APIResponse(status="error", message="仅支持 jpeg/png 图片", data={"error_code": "BAD_TYPE"})

    # 画像须存在（头像属于画像）
    row = db.query(UserProfileModel).filter(UserProfileModel.user_id == user_id).first()
    if row is None:
        return APIResponse(status="error", message="画像不存在，请先建立画像", data={"error_code": "NO_PROFILE"})

    # 原子写：临时文件 + os.replace，防并发覆盖写坏
    os.makedirs(AVATAR_DIR, exist_ok=True)
    final_path = os.path.join(AVATAR_DIR, f"{user_id}.{ext}")
    tmp_path = final_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)
    os.replace(tmp_path, final_path)

    url = f"/static/avatars/{user_id}.{ext}"
    row.avatar_url = url
    db.commit()
    return APIResponse(status="success", message="头像已更新", data={"avatar_url": url})


# ============================================================================
# API 5: 获取画像（GET /api/resume/profile）
# ============================================================================

@resume_router.get("/profile")
async def get_profile_endpoint(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    db: Session = Depends(get_db)
):
    """
    获取个人画像（从数据库读取）。

    无画像时返回 profile=None，前端可据此引导用户先建立画像。
    """
    try:
        if not user_id:
            return APIResponse(status="error", message="缺少 user_id", data=None)

        profile = get_profile_service(db, user_id)
        if profile is None:
            return APIResponse(
                status="success",
                message="暂无画像",
                data={"user_id": user_id, "profile": None}
            )

        confidence = get_profile_confidence(db, user_id)
        return APIResponse(
            status="success",
            message="获取画像成功",
            data={
                "user_id": user_id,
                "profile": profile,
                "confidence": confidence
            }
        )

    except Exception as e:
        return APIResponse(
            status="error",
            message=f"获取画像失败：{str(e)}",
            data=None
        )


# ============================================================================
# API 6: 导出画像（GET /api/resume/export-profile）
# ============================================================================

@resume_router.get("/export-profile")
async def export_profile(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    format: str = Query("json", description="导出格式：json 或 markdown"),
    db: Session = Depends(get_db)
):
    """
    导出个人画像（从数据库读取真实画像）

    Args:
        user_id: 用户 ID
        format: 导出格式（json 或 markdown）

    Returns:
        JSONResponse: 导出的画像（json 直接返回画像 dict；markdown 返回文本）
    """
    try:
        if not user_id:
            return JSONResponse(
                content={"status": "error", "message": "缺少 user_id", "data": None}
            )

        profile = get_profile_service(db, user_id)
        if profile is None:
            return JSONResponse(
                content={"status": "error", "message": "暂无画像，无法导出", "data": None}
            )

        if format.lower() == "json":
            # 直接返回画像 dict
            return JSONResponse(
                content={"status": "success", "message": "导出成功", "data": profile}
            )

        elif format.lower() == "markdown":
            # 用画像关键字段生成简易 Markdown
            name = profile.get("name") or "（未提供）"
            phone = profile.get("phone") or "（未提供）"
            email = profile.get("email") or "（未提供）"
            markdown = f"""# 个人画像

## 基本信息
- 姓名：{name}
- 电话：{phone}
- 邮箱：{email}

---
*求职 Copilot*
"""
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "导出成功",
                    "data": {"markdown": markdown}
                }
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的格式：{format}。仅支持 json 和 markdown。"
            )

    except HTTPException:
        raise

    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": f"导出失败：{str(e)}",
                "data": None
            }
        )


# ============================================================================
# API 7: 删除画像（DELETE /api/resume/profile）
# ============================================================================

@resume_router.delete("/profile")
async def delete_profile_endpoint(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    db: Session = Depends(get_db)
):
    """
    删除个人画像（从数据库删除）

    Args:
        user_id: 用户 ID

    Returns:
        APIResponse: 删除结果（deleted=True 表示实际删除；False 表示本就无画像）
    """
    try:
        if not user_id:
            return APIResponse(status="error", message="缺少 user_id", data=None)

        deleted = delete_profile_service(db, user_id)
        if not deleted:
            return APIResponse(
                status="success",
                message="本就无画像，无需删除",
                data={"user_id": user_id, "deleted": False}
            )

        return APIResponse(
            status="success",
            message="画像已删除",
            data={"user_id": user_id, "deleted": True}
        )

    except Exception as e:
        return APIResponse(
            status="error",
            message=f"删除画像失败：{str(e)}",
            data=None
        )


# ============================================================================
# API 8: 获取示例简历（GET /api/resume/sample-resumes）
# ============================================================================

@resume_router.get("/sample-resumes")
async def get_sample_resumes():
    """
    获取示例简历列表

    Returns:
        APIResponse: 示例简历列表
    """
    try:
        # TODO: 从数据库或文件系统读取
        # MVP 阶段：返回示例数据

        samples = [
            {
                "id": "sample_1",
                "name": "标准产品经理简历",
                "description": "高质量简历，包含完整的教育、工作、技能信息",
                "tags": ["产品经理", "互联网", "完整"]
            },
            {
                "id": "sample_2",
                "name": "技术负责人简历",
                "description": "复杂排版，包含多个项目经验和技术栈",
                "tags": ["技术", "开发", "复杂"]
            },
            {
                "id": "sample_3",
                "name": "应届生简历",
                "description": "简短简历，适合应届生参考",
                "tags": ["应届生", "简短", "实习"]
            }
        ]

        return APIResponse(
            status="success",
            message="获取示例简历成功（MVP 阶段返回示例数据）",
            data={
                "samples": samples,
                "count": len(samples)
            }
        )

    except Exception as e:
        return APIResponse(
            status="error",
            message=f"获取示例简历失败：{str(e)}",
            data=None
        )


# ============================================================================
# 健康检查端点
# ============================================================================

@resume_router.get("/health")
async def health_check():
    """
    简历解析模块健康检查

    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "module": "resume_parser",
        "upload_dir": RESUME_UPLOAD_DIR,
        "max_file_size": f"{MAX_FILE_SIZE / 1024 / 1024}MB"
    }
