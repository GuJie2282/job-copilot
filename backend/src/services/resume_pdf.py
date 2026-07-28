"""
简历 PDF 渲染服务（resume_pdf）

用 Playwright chromium 把预览页 HTML 渲染为 A4 PDF（字节）。
取代前端浏览器打印对话框：服务端渲染、点一下直接下载、排版精确可控。

设计（对应 evolve-resume-refine design 决策 7）：
- page.pdf() 走 @media print：preview_shell 的 @page A4 + .page page-break 生效
- set_content 后等 DOMContentLoaded + 分页 JS 跑完，再出 PDF
- print_background=True 保留主题色（oklch）
- margin 0：preview_shell 的 @page margin 0，.page 自带 padding

降级：渲染失败时调用方 catch，回退浏览器打印通道（spec「服务端渲染失败降级」）。

作者：求职 Copilot 项目
日期：2026-07-24
"""
import asyncio
import base64
import logging
import os
import re
import sys
from typing import Optional, Tuple

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

# 静态资源根（与 main.py 的 StaticFiles mount 一致：backend/data）
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STATIC_DIR = os.path.join(_BACKEND_ROOT, "data")

# 匹配 src="/static/..." 相对图片 URL（add-resume-avatar：PDF 内联兜底）
_STATIC_SRC_RE = re.compile(r'src="(\/static\/([^"]+))"')


def _inline_static_images(html: str) -> str:
    """把 HTML 里 /static/... 相对图片 URL 转成 base64 data URL。

    Playwright set_content 的 base URL 是 about:blank，不解析相对 URL（/static/x.jpg 加载失败）；
    set_content 也不支持 base_url（page.goto 才支持）。故渲染前内联成 data URL，HTML 自包含。
    """
    def _repl(m):
        rel_parts = m.group(2).split('/')  # 例：avatars / xxx.jpg
        full_path = os.path.join(_STATIC_DIR, *rel_parts)
        try:
            with open(full_path, 'rb') as f:
                data = f.read()
            ext = os.path.splitext(full_path)[1].lower().lstrip('.')
            mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png'}.get(ext, 'image/png')
            b64 = base64.b64encode(data).decode('ascii')
            return f'src="data:{mime};base64,{b64}"'
        except Exception as e:
            logger.warning(f"PDF 图片内联失败（{m.group(1)}）：{e}")
            return m.group(0)  # 失败保留原 URL（降级）
    return _STATIC_SRC_RE.sub(_repl, html)


def render_html_to_pdf(html: str, *, wait_ms: int = 500) -> Tuple[bytes, int]:
    """
    把完整预览页 HTML 渲染为 A4 PDF（同步 API）。

    ⚠️ Windows + uvicorn：uvicorn 的事件循环不支持 asyncio 子进程（create_subprocess_exec
    抛 NotImplementedError），而 Playwright 启动 chromium 正是子进程。故用同步 API，由调用方
    经 asyncio.to_thread 放线程池跑——线程内 sync_playwright 自建支持子进程的事件循环。

    Args:
        html:    wrap_preview 产出的完整页（含 preview_shell + 主题 + 原子）
        wait_ms: 渲染后等待毫秒（确保字体/分页 JS 就绪）
    Returns:
        (pdf_bytes, page_count)：PDF 字节 + 实际页数（数 .page，精确排版度量）
    Raises:
        Playwright 启动/渲染异常（调用方 catch 做降级）
    """
    # Windows + uvicorn：uvicorn 用 SelectorEventLoop（不支持子进程），全局 policy 亦然。
    # sync_playwright 在线程内 new_event_loop 读全局 policy → 仍 Selector → 子进程 NotImplementedError。
    # 故临时切 Proactor policy，让 sync_playwright 用支持子进程的循环；渲染后恢复原 policy。
    old_policy = asyncio.get_event_loop_policy() if sys.platform == 'win32' else None
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                # domcontentloaded + 显式等分页（不用 networkidle：preview_shell 的 fonts.ready 会让它迟迟不达）
                page.set_content(_inline_static_images(html), wait_until='domcontentloaded')
                try:
                    page.wait_for_selector('#scaler .page', timeout=5000)
                except Exception:
                    pass  # 分页未就绪也继续（降级用当前 DOM 出 PDF）
                if wait_ms:
                    page.wait_for_timeout(wait_ms)
                page_count = page.evaluate(
                    "() => document.querySelectorAll('#scaler .page').length || 1"
                )
                pdf = page.pdf(
                    format='A4', print_background=True,
                    margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'},
                )
                return pdf, int(page_count)
            finally:
                browser.close()
    finally:
        if old_policy is not None:
            asyncio.set_event_loop_policy(old_policy)
