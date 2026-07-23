"""
语音转写 API 路由（add-voice-interview）
========================================

端点：
  POST /api/interview/voice/transcribe  上传音频 → 返回识别文本

零侵入（design.md 决策 4）：本端点只做「音频 → 文本」，识别结果由前端以
answer 文本接入现有 submitAnswer 链路。整个 LangGraph 面试子图、checkpointer
不感知回答来源是文字还是语音。

鉴权：跟随项目现有范式（前端传 user_id，非强制 token 校验，与 resume/interview 一致）。

错误码透传（design.md 决策 9）：失败时 data.error_code 透传 voice_service 的错误码，
前端据此给不同降级提示：
  - EMPTY_AUDIO / NO_CONTENT → 「未识别到内容，请重新回答」
  - DECODE_FAILED            → 「音频格式异常」
  - TRANSCRIBE_ERROR         → 「识别失败，可重试或切文字」

作者：求职 Copilot 项目
日期：2026-07-22
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, Query
from pydantic import BaseModel, Field

from src.services.voice_service import transcribe_audio

logger = logging.getLogger(__name__)

voice_router = APIRouter()

# 音频大小上限。30s webm/opus 实际仅几十 KB，留足余量防滥用。
MAX_AUDIO_SIZE = 25 * 1024 * 1024


class ApiResponse(BaseModel):
    """统一响应（与 interview/resume 一致）。"""
    status: str = Field(..., description="success / error")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


@voice_router.post("/transcribe", response_model=ApiResponse)
async def transcribe_voice(
    file: UploadFile = File(..., description="音频文件（webm/wav/mp3 等，浏览器 MediaRecorder 录制）"),
    user_id: Optional[str] = Query(None, description="用户 ID（可选，用于日志追溯）"),
):
    """
    语音转文本。

    前端录音结束后上传音频，拿到识别文本，再以 answer 文本调用 submitAnswer
    （与文字模式汇合，复用整条答题链路）。
    """
    try:
        audio = await file.read()

        # 大小校验
        if len(audio) > MAX_AUDIO_SIZE:
            return ApiResponse(
                status="error",
                message=f"音频过大（{len(audio) / 1024 / 1024:.1f}MB），上限 {MAX_AUDIO_SIZE // 1024 // 1024}MB",
                data={"error_code": "AUDIO_TOO_LARGE"},
            )

        # 转写
        result = transcribe_audio(audio, file.filename or "audio.webm")

        if result.ok:
            logger.info(f"语音转写成功（user={user_id}）：{len(result.text)} 字")
            return ApiResponse(
                status="success",
                message="语音识别成功",
                data={"text": result.text},
            )

        # 失败：透传 error_code，前端按 code 给不同降级提示
        logger.info(f"语音转写失败（user={user_id}）：{result.error} - {result.message}")
        return ApiResponse(
            status="error",
            message=result.message,
            data={"error_code": result.error},
        )

    except Exception as e:
        logger.warning(f"语音端点异常：{type(e).__name__}: {e}")
        return ApiResponse(
            status="error",
            message=f"语音上传处理失败：{type(e).__name__}",
            data={"error_code": "UPLOAD_ERROR"},
        )
