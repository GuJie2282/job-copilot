"""
语音转写服务（voice_service）
==============================

把用户面试时的语音回答转成文本。是 add-voice-interview 的后端核心，
被 /api/interview/voice/transcribe 端点调用。

技术选型（design.md 决策 1/2/3，spike 已验证可行）：
  - 引擎：faster-whisper（OpenAI Whisper 的 CTranslate2 加速版，MIT 开源、本地部署）
  - 模型：small（spike 实测中文准确率 95%+，CPU 延迟 ~4-6s / 10s 音频，实时率 2.7x）
  - 解码：PyAV 直读 webm/opus（spike 验证：无需 pydub/ffmpeg 转码层，架构更简）
  - 模式：批处理（录完再识别），非流式

模型单例懒加载：首次调用时加载（首次会从 HuggingFace 下载 ~488MB），后续复用。
HuggingFace 下载配置见模块顶部（spike 踩坑：必须禁用 xet 协议，否则 401）。

返回 TranscribeResult，明确区分四类失败，前端据 error 码给出不同降级提示
（对应 spec「语音模式降级」）：
  - EMPTY_AUDIO        上传音频为空
  - DECODE_FAILED      解码失败（格式损坏/不支持）
  - NO_CONTENT         转写成功但无内容（录音太短/无声）
  - TRANSCRIBE_ERROR   转写过程异常

作者：求职 Copilot 项目
日期：2026-07-22
"""

import os
import logging
import tempfile
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 配置常量（均可经环境变量覆盖）
# ============================================================================

# Whisper 模型档位。spike 验证 small 是中文质量与 CPU 延迟的最佳平衡。
# 可经 WHISPER_MODEL 覆盖：tiny(最快/质量降) / base / small(默认) / medium(更准/更慢)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")      # CPU 部署（MVP 无 GPU）
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")   # int8 量化（CPU 最快，质量损失可忽略）
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "zh")   # 中文面试，强制中文识别

# 单段录音时长上限（秒）—— spec 边界：建议 5s-5min，超时由前端自动结束，后端再兜底
MAX_AUDIO_SECONDS = 5 * 60


# ============================================================================
# HuggingFace 下载配置（spike 踩坑记录，避免重蹈）
# ============================================================================
# 新版 huggingface-hub（≥1.0）默认用 xet 协议下大文件，走 cas-server.xethub.hf.co，
# 国内访问返 401 Unauthorized。必须禁用 xet 回退普通 HTTP，才能配合 HF 镜像下载。
# setdefault 不覆盖用户已在环境/.env 设置的值。
#   HF_ENDPOINT（镜像）由用户在 .env 按需配：国内推荐 HF_ENDPOINT=https://hf-mirror.com
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


# ============================================================================
# 模型单例
# ============================================================================

_model = None  # WhisperModel 单例（懒加载，避免 import 时就下载模型）


def get_model():
    """
    获取 faster-whisper 模型单例。首次调用时加载（首次会从 HuggingFace 下载模型权重）。

    单例避免每次请求重载模型（加载 ~1s，下载仅首次）。线程安全由 GIL 兜底
    （极端并发下可能重复加载一次，无害——后续单例覆盖即可）。
    """
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info(
            f"加载 faster-whisper 模型：{WHISPER_MODEL}"
            f"（device={WHISPER_DEVICE}, compute={WHISPER_COMPUTE}）。首次会下载权重，请稍候…"
        )
        _model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE,
        )
        logger.info("faster-whisper 模型加载完成")
    return _model


# ============================================================================
# 转写结果
# ============================================================================

@dataclass
class TranscribeResult:
    """
    转写结果。前端据 ok 与 error 给出不同降级提示（spec「语音模式降级」）。

    成功：ok=True, text=识别文本
    失败：ok=False, error=错误码, message=可读消息
    """
    ok: bool
    text: str = ""
    error: Optional[str] = None
    message: str = ""

    # —— 错误码常量（类属性，非 dataclass 字段）——
    EMPTY_AUDIO = "EMPTY_AUDIO"              # 上传音频为空
    DECODE_FAILED = "DECODE_FAILED"          # 解码失败（格式损坏/不支持）
    NO_CONTENT = "NO_CONTENT"                # 转写成功但无内容（太短/无声）
    TRANSCRIBE_ERROR = "TRANSCRIBE_ERROR"    # 转写过程异常


# ============================================================================
# 核心转写函数
# ============================================================================

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> TranscribeResult:
    """
    把音频字节转写为文本。

    Args:
        audio_bytes: 音频原始字节（浏览器录的 webm/opus，或 wav/mp3 等，PyAV 自动识别）
        filename:    原始文件名（仅用于取扩展名辅助，PyAV 按内容识别格式）

    Returns:
        TranscribeResult：成功含 text；失败含 error 码

    流程：
        1. 校验音频非空
        2. 写临时文件（faster-whisper 接文件路径，PyAV 自动解码 webm/opus/wav 等）
        3. model.transcribe（VAD 过滤静音 + 强制中文）
        4. 空文本判为 NO_CONTENT（录音太短/无声）
        5. finally 清理临时文件（不持久化音频）
    """
    # 1. 空音频校验
    if not audio_bytes:
        return TranscribeResult(ok=False, error=TranscribeResult.EMPTY_AUDIO, message="音频为空")

    tmp_path = None
    try:
        # 2. 写临时文件（保留原扩展名，PyAV 主要按内容识别但扩展名有助于个别格式）
        ext = os.path.splitext(filename)[-1] or ".webm"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        # 3. 转写
        model = get_model()
        segments, info = model.transcribe(
            tmp_path,
            language=WHISPER_LANGUAGE,
            vad_filter=True,     # 过滤静音段，提升质量与速度
            beam_size=5,
            # Whisper small 中文输出繁简不稳（spike 实测：同模型有时简体有时繁体）。
            # 用简体 initial_prompt 引导输出简体——Whisper 社区经典技巧：
            # initial_prompt 作为"上文"暗示解码风格，中性短句不会污染识别内容。
            initial_prompt="以下是普通话的句子。",
        )
        # transcribe 是 lazy generator，list()/迭代触发实际转写
        text = "".join(s.text for s in segments).strip()

        # 时长上限兜底（前端已限，这里仅记日志）
        if info.duration > MAX_AUDIO_SECONDS:
            logger.warning(f"音频时长 {info.duration:.1f}s 超上限 {MAX_AUDIO_SECONDS}s")

        # 4. 空内容判定
        if not text:
            return TranscribeResult(
                ok=False, error=TranscribeResult.NO_CONTENT,
                message="未识别到内容（录音可能过短或无声）",
            )

        logger.info(f"语音转写成功：{info.duration:.1f}s 音频 → {len(text)} 字")
        return TranscribeResult(ok=True, text=text, message="转写成功")

    except Exception as e:
        logger.warning(f"语音转写失败：{type(e).__name__}: {e}")
        # 区分解码失败（格式问题）与其他转写异常，前端给不同提示
        msg = str(e).lower()
        if any(k in msg for k in ("decode", "demux", "codec", "averror", "invalid data", "invaliddata", "format")):
            return TranscribeResult(
                ok=False, error=TranscribeResult.DECODE_FAILED,
                message=f"音频解码失败：{type(e).__name__}",
            )
        return TranscribeResult(
            ok=False, error=TranscribeResult.TRANSCRIBE_ERROR,
            message=f"转写异常：{type(e).__name__}",
        )
    finally:
        # 5. 清理临时文件（不持久化音频）
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# ============================================================================
# 主函数（自检）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("voice_service 自检（pyttsx3 生成中文 wav → 转写）")
    print("=" * 60)
    import pyttsx3
    engine = pyttsx3.init()
    for v in engine.getProperty('voices'):
        if 'ZH-CN' in (getattr(v, 'id', '') or '').upper():
            engine.setProperty('voice', v.id)
            break
    test = "这是一段语音转写服务的自检文本，包含产品经理、转化率等专业术语。"
    _tmp = os.path.join(tempfile.gettempdir(), "voice_selfcheck.wav")
    engine.save_to_file(test, _tmp)
    engine.runAndWait()
    with open(_tmp, "rb") as f:
        audio = f.read()
    os.remove(_tmp)

    print(f"\n原文：{test}")
    result = transcribe_audio(audio, "selfcheck.wav")
    print(f"结果：ok={result.ok} error={result.error} message={result.message}")
    print(f"识别：{result.text}")
