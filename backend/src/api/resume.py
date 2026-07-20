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
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# 导入服务
from src.services.resume_parser import parse_resume, deduplicate_text
from src.services.quality_checker import check_text_quality, calculate_profile_confidence
from src.services.llm_retry import invoke_llm_with_retry, is_retryable
from src.services.profile_service import (
    save_profile,
    get_profile as get_profile_service,
    get_profile_confidence,
    delete_profile as delete_profile_service,
)
from src.core.deps import get_db
from src.graph.config import get_structured_llm, UserProfile
from src.graph.prompts import get_extraction_prompt


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
    import json
    import re
    import time
    import logging
    from src.graph.config import get_llm
    from src.graph.prompts import get_json_extraction_prompt

    logger = logging.getLogger(__name__)
    llm = get_llm(temperature=0.0)
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            prompt = get_json_extraction_prompt(text, quality_score)
            # 重试时强化 JSON 格式要求（LLM 偶发返回非 JSON 时尤其有效）
            if attempt > 0:
                prompt = (
                    "上次提取失败。请严格输出合法 JSON，必须包裹在 ```json 代码块中，"
                    "不要输出任何解释或多余文字。\n\n" + prompt
                )

            # 调用 LLM（API 异常会被下面的 except 捕获并重试）
            response = llm.invoke(prompt)
            response_text = response.content

            # 提取 JSON（处理 markdown 代码块包裹的情况）
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            json_text = json_match.group(1) if json_match else response_text.strip()

            # 解析 JSON：先标准解析，失败则用 json_repair 容错修复。
            # glm-4-flash 等弱模型输出「含长文本详情」的大 JSON 时，偶发缺逗号 / 引号转义错，
            # json_repair 能修复这类轻微格式错误，避免直接判失败、反复重试浪费时间。
            try:
                profile_dict = json.loads(json_text)
            except json.JSONDecodeError as je:
                try:
                    from json_repair import repair_json
                    profile_dict = repair_json(json_text, return_objects=True)
                    logger.warning(
                        f"标准 JSON 解析失败，已用 json_repair 容错修复：{je}。"
                        f"LLM 原始输出前 300 字：{response_text[:300]}"
                    )
                except Exception:
                    # json_repair 也修不了 → 抛原错误，触发外层重试
                    raise je

            # Pydantic 校验
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
        llm = get_structured_llm(schema=UserProfile, temperature=0.0)
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
