"""
简历解析模块

功能：
1. PDF 解析（pdfplumber 主解析器，PyPDF2 备选）
2. Word 解析（python-docx）
3. 快速检测（加密、扫描件、大小检查）

作者：求职 Copilot 项目
日期：2026-07-03
"""

import os
import io
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

# PDF 解析库
import pdfplumber
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

# Word 解析库
from docx import Document


# ============================================================================
# 常量定义
# ============================================================================

# 文件大小限制（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# 扫描件检测阈值（如果文本提取少于 100 字符，可能是扫描件）
SCANNED_PDF_THRESHOLD = 100

# 支持的文件格式
SUPPORTED_FORMATS = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
}


# ============================================================================
# 异常类定义
# ============================================================================

class ResumeParserError(Exception):
    """简历解析基础异常"""
    pass


class FileTooLargeError(ResumeParserError):
    """文件过大异常"""
    pass


class EncryptedPDFError(ResumeParserError):
    """PDF 加密异常"""
    pass


class ScannedPDFError(ResumeParserError):
    """扫描件 PDF 异常"""
    pass


class UnsupportedFormatError(ResumeParserError):
    """不支持的文件格式异常"""
    pass


class FileCorruptedError(ResumeParserError):
    """文件损坏异常"""
    pass


# ============================================================================
# 文本去重（PDF 提取常见问题：同一行/段落被重复提取）
# ============================================================================

def deduplicate_text(text: str) -> str:
    """
    去除 PDF/Word 提取时常见的重复内容。

    解析器（pdfplumber / PyPDF2 / python-docx）对某些文件会把内容重复提取，常见三种形态：
    1. 同一行被连续重复（文本层重叠）—— 例如「2022年09月 - 2026年06月」紧挨着出现两次
    2. 「标题A 标题B 标题A 标题B」交替重复（双栏错位）—— 例如「个人总结 / 实习经历」来回出现
    3. 整段经历或项目被原样重复 N 次（多页重复、段落+表格双提取）—— 例如整块项目经历重复 4 遍

    只靠「连续行去重」能处理形态 1，但抓不住形态 2、3（因为相邻行内容不同）。
    因此分两步处理：
      第一步：连续重复行去重（清理块内紧邻的重复行）。
      第二步：段落块去重——按空行把文本切成「块」，内容完全相同的块只保留第一次出现。
    只做「完全相同」的合并，不做模糊去重，避免误删简历里合理重复的内容
    （如多个项目都提到「Python」、多个岗位都写「需求分析」）。

    Args:
        text: 提取的原始文本

    Returns:
        去重后的文本
    """
    import re

    if not text:
        return text

    # ---- 第一步：连续重复行去重 ----
    # 和「上一个非空行」比较（即便中间隔着空行，如 docx 的 \n\n 段落分隔）
    lines = text.split('\n')
    deduped = []
    last_non_empty = None
    for line in lines:
        stripped = line.strip()
        if stripped:
            if last_non_empty == stripped:
                continue
            last_non_empty = stripped
            deduped.append(line)
        else:
            # 空行：只在上一行非空时保留一个，压缩连续空行
            if deduped and deduped[-1].strip():
                deduped.append('')
    once = '\n'.join(deduped)

    # ---- 第二步：段落块去重（整段完全相同才合并）----
    # 按一行或多行空行把文本切成「块」；归一化 key 时把所有空白压成单空格再比较，
    # 这样「个人总结\n实习经历」与「个人总结\n\n实习经历」会被识别为同一块。
    raw_blocks = re.split(r'\n[ \t]*\n+', once)
    seen = set()
    unique_blocks = []
    for block in raw_blocks:
        key = re.sub(r'\s+', ' ', block).strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique_blocks.append(block.strip())

    return '\n\n'.join(unique_blocks)


# ============================================================================
# 快速检测功能
# ============================================================================

def quick_check(file_path: str, file_size: int) -> Tuple[bool, Optional[str]]:
    """
    快速检测文件是否可以解析

    Args:
        file_path: 文件路径
        file_size: 文件大小（字节）

    Returns:
        (is_valid, error_message)
        - is_valid: 是否可以通过快速检测
        - error_message: 如果检测失败，返回错误信息；否则返回 None

    检测项目：
    1. 文件大小（不超过 10MB）
    2. PDF 是否加密
    3. PDF 是否是扫描件（通过文本长度判断）
    """
    # 1. 检查文件大小
    if file_size > MAX_FILE_SIZE:
        return False, f"文件过大（{file_size / 1024 / 1024:.2f}MB），最大支持 10MB。文件过大可能是扫描件，建议使用可搜索的 PDF 或复制粘贴文本。"

    # 2. 检查文件扩展名
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in ['.pdf', '.docx']:
        return False, f"不支持的文件格式：{file_ext}。仅支持 PDF 和 Word 文档（.docx）。"

    # 3. 如果是 PDF，检查是否加密或扫描件
    if file_ext == '.pdf':
        try:
            # 检查是否加密
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                if reader.is_encrypted:
                    return False, "PDF 文件已加密，请先解除密码保护后重新上传。"

                # 快速检测是否是扫描件（读取第一页）
                if len(reader.pages) > 0:
                    first_page = reader.pages[0]
                    # extract_text() 可能返回 None（如纯图片页），用 or "" 兜底
                    text = first_page.extract_text() or ""
                    if len(text.strip()) < SCANNED_PDF_THRESHOLD:
                        return False, f"这可能是扫描件 PDF（提取的文本少于 {SCANNED_PDF_THRESHOLD} 字符）。扫描件无法解析，建议：1) 复制粘贴文本 2) 使用可搜索的 PDF 3) 手动填写画像。"

        except PdfReadError as e:
            return False, f"PDF 文件损坏或格式不支持：{str(e)}"
        except Exception as e:
            return False, f"读取 PDF 文件时出错：{str(e)}"

    # 4. 如果是 Word 文档，检查是否能打开
    elif file_ext == '.docx':
        try:
            doc = Document(file_path)
            # 尝试读取第一段文字，验证文件是否损坏
            if len(doc.paragraphs) > 0:
                _ = doc.paragraphs[0].text
        except Exception as e:
            return False, f"Word 文档损坏或格式不支持：{str(e)}"

    # 所有检测通过
    return True, None


# ============================================================================
# PDF 解析功能（pdfplumber - 主解析器）
# ============================================================================

def parse_pdf_with_pdfplumber(file_path: str) -> Tuple[str, Optional[str]]:
    """
    使用 pdfplumber 解析 PDF 文件

    Args:
        file_path: PDF 文件路径

    Returns:
        (extracted_text, error_message)
        - extracted_text: 提取的文本内容
        - error_message: 如果解析失败，返回错误信息；否则返回 None
    """
    try:
        text_parts = []

        with pdfplumber.open(file_path) as pdf:
            # 遍历所有页面
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # 提取文本
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    # 某一页解析失败，继续解析其他页
                    print(f"[WARNING] Page {page_num} extraction failed: {e}")
                    continue

        # 合并所有页面的文本
        full_text = "\n\n".join(text_parts)

        # 检查提取的文本是否过少（可能是扫描件）
        if len(full_text.strip()) < SCANNED_PDF_THRESHOLD:
            return "", f"提取的文本过少（{len(full_text.strip())} 字符），可能是扫描件 PDF。建议：1) 复制粘贴文本 2) 使用可搜索的 PDF 3) 手动填写画像。"

        return full_text, None

    except Exception as e:
        return "", f"pdfplumber 解析失败：{str(e)}"


# ============================================================================
# PDF 解析功能（PyPDF2 - 备选解析器）
# ============================================================================

def parse_pdf_with_pypdf2(file_path: str) -> Tuple[str, Optional[str]]:
    """
    使用 PyPDF2 解析 PDF 文件（备选方案）

    Args:
        file_path: PDF 文件路径

    Returns:
        (extracted_text, error_message)
        - extracted_text: 提取的文本内容
        - error_message: 如果解析失败，返回错误信息；否则返回 None
    """
    try:
        text_parts = []

        with open(file_path, 'rb') as f:
            reader = PdfReader(f)

            # 遍历所有页面
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    # 提取文本
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    # 某一页解析失败，继续解析其他页
                    print(f"[WARNING] Page {page_num} extraction failed: {e}")
                    continue

        # 合并所有页面的文本
        full_text = "\n\n".join(text_parts)

        # 检查提取的文本是否过少（可能是扫描件）
        if len(full_text.strip()) < SCANNED_PDF_THRESHOLD:
            return "", f"提取的文本过少（{len(full_text.strip())} 字符），可能是扫描件 PDF。建议：1) 复制粘贴文本 2) 使用可搜索的 PDF 3) 手动填写画像。"

        return full_text, None

    except PdfReadError as e:
        return "", f"PyPDF2 解析失败（PDF 可能损坏）：{str(e)}"
    except Exception as e:
        return "", f"PyPDF2 解析失败：{str(e)}"


# ============================================================================
# PDF 解析统一接口（自动选择解析器）
# ============================================================================

def parse_pdf(file_path: str) -> Tuple[str, Optional[str], str]:
    """
    解析 PDF 文件（自动选择解析器）

    优先使用 pdfplumber，如果失败则使用 PyPDF2

    Args:
        file_path: PDF 文件路径

    Returns:
        (extracted_text, error_message, parser_used)
        - extracted_text: 提取的文本内容
        - error_message: 如果解析失败，返回错误信息；否则返回 None
        - parser_used: 使用的解析器（"pdfplumber" 或 "PyPDF2"）
    """
    # 首先尝试 pdfplumber
    text, error = parse_pdf_with_pdfplumber(file_path)
    if text:
        return text, None, "pdfplumber"

    # 如果 pdfplumber 失败，尝试 PyPDF2
    print(f"[INFO] pdfplumber failed: {error}. Trying PyPDF2...")
    text, error = parse_pdf_with_pypdf2(file_path)
    if text:
        return text, None, "PyPDF2"

    # 两个解析器都失败
    return "", error or "PDF 解析失败，请尝试其他格式或手动填写。", "none"


# ============================================================================
# Word 文档解析功能
# ============================================================================

def parse_docx(file_path: str) -> Tuple[str, Optional[str]]:
    """
    解析 Word 文档（.docx）

    Args:
        file_path: Word 文档路径

    Returns:
        (extracted_text, error_message)
        - extracted_text: 提取的文本内容
        - error_message: 如果解析失败，返回错误信息；否则返回 None
    """
    try:
        doc = Document(file_path)
        text_parts = []

        # 提取所有段落的文本
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text.strip())

        # 提取表格中的文本（如果有）
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_parts.append(cell.text.strip())

        # 合并所有文本
        full_text = "\n\n".join(text_parts)

        if not full_text.strip():
            return "", "Word 文档为空或无法提取文本。"

        return full_text, None

    except Exception as e:
        return "", f"Word 文档解析失败：{str(e)}"


# ============================================================================
# 头像提取（add-resume-avatar）：从简历文件提取证件照
# 只返回 (image_bytes, ext)，存盘与 URL 由调用方（API 层）负责。
# ============================================================================

def _image_ext_from_magic(data: bytes) -> Optional[str]:
    """根据文件头魔数判断图片类型，返回扩展名（jpg/png）；不认识返回 None。"""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return None


def extract_pdf_avatar(file_path: str) -> Optional[Tuple[bytes, str]]:
    """
    从 PDF 首页提取最像证件照的图片（几何启发式）。

    筛选：位于页面上半部（top < 页高/2）+ 宽高比 0.7~1.3 + 边长 80~400pt；
    按「越靠左上 + 越接近正方形」打分，取最高分一张。

    Returns:
        (image_bytes, ext) 或 None（无合适图 / 提取失败）。失败降级返回 None，不抛异常。
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                return None
            page = pdf.pages[0]
            page_w, page_h = page.width, page.height
            candidates = []  # [(score, img_dict), ...]
            for img in page.images:
                x0, top, x1, bottom = img["x0"], img["top"], img["x1"], img["bottom"]
                w, h = x1 - x0, bottom - top
                if w <= 0 or h <= 0:
                    continue
                # 上半页（简历头像通常在顶部）
                if top > page_h / 2:
                    continue
                ratio = w / h
                # 宽高比接近正方形（证件照）
                if not (0.7 <= ratio <= 1.3):
                    continue
                # 尺寸合理（排除小图标/logo，排除大背景图）
                if not (80 <= w <= 400 and 80 <= h <= 400):
                    continue
                # 打分：靠上 + 靠左 + 接近正方形
                score = (page_h / 2 - top) + (page_w - x0) + (1 - abs(ratio - 1)) * 100
                candidates.append((score, img))
            if not candidates:
                return None
            candidates.sort(key=lambda c: c[0], reverse=True)
            best = candidates[0][1]
            bbox = (best["x0"], best["top"], best["x1"], best["bottom"])
            cropped = page.within_bbox(bbox).extract_image()
            ext = _image_ext_from_magic(cropped["image_bytes"]) or cropped.get("ext") or "png"
            return cropped["image_bytes"], ext
    except Exception as e:
        print(f"[WARNING] extract_pdf_avatar failed: {e}")
        return None


def extract_docx_avatar(file_path: str) -> Optional[Tuple[bytes, str]]:
    """
    从 docx 提取首个内嵌图片作为头像（python-docx 遍历 part.rels 找图片部件）。

    Returns:
        (image_bytes, ext) 或 None（无图 / 提取失败）。失败降级返回 None，不抛异常。
    """
    try:
        doc = Document(file_path)
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:  # 图片关系（RT.IMAGE）
                blob = rel.target_part.blob
                ext = _image_ext_from_magic(blob) or "png"
                return blob, ext
        return None
    except Exception as e:
        print(f"[WARNING] extract_docx_avatar failed: {e}")
        return None


# ============================================================================
# 统一解析接口（根据文件类型自动选择解析器）
# ============================================================================

def parse_resume(file_path: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    解析简历文件（PDF 或 Word）

    Args:
        file_path: 文件路径

    Returns:
        (result, error_message)
        - result: 解析结果字典，包含：
            - text: 提取的文本内容
            - parser: 使用的解析器（"pdfplumber", "PyPDF2", "python-docx"）
            - file_size: 文件大小（字节）
            - file_ext: 文件扩展名
        - error_message: 如果解析失败，返回错误信息；否则返回 None

    示例：
        >>> result, error = parse_resume("resume.pdf")
        >>> if error:
        >>>     print(f"解析失败: {error}")
        >>> else:
        >>>     print(f"提取的文本: {result['text']}")
        >>>     print(f"使用的解析器: {result['parser']}")
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return {}, f"文件不存在：{file_path}"

    # 获取文件信息
    file_size = os.path.getsize(file_path)
    file_ext = Path(file_path).suffix.lower()

    # 快速检测
    is_valid, error_msg = quick_check(file_path, file_size)
    if not is_valid:
        return {}, error_msg

    # 根据文件类型选择解析器
    extracted_text = ""
    parser_used = "none"
    error_message = None

    if file_ext == '.pdf':
        extracted_text, error_message, parser_used = parse_pdf(file_path)
    elif file_ext == '.docx':
        extracted_text, error_message = parse_docx(file_path)
        parser_used = "python-docx"
    else:
        return {}, f"不支持的文件格式：{file_ext}"

    # 如果解析失败
    if error_message:
        return {}, error_message

    # 文本去重（处理 PDF/Word 提取时的连续重复行）
    extracted_text = deduplicate_text(extracted_text)

    # 返回解析结果
    result = {
        'text': extracted_text,
        'parser': parser_used,
        'file_size': file_size,
        'file_ext': file_ext,
        'text_length': len(extracted_text)
    }

    return result, None


# ============================================================================
# 主函数（测试用）
# ============================================================================

if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("简历解析模块测试")
    print("=" * 60)

    # 示例：解析一个 PDF 文件
    test_file = "test_resume.pdf"

    if os.path.exists(test_file):
        print(f"\n[TEST] 正在解析文件: {test_file}")

        result, error = parse_resume(test_file)

        if error:
            print(f"[ERROR] 解析失败: {error}")
        else:
            print(f"[SUCCESS] 解析成功!")
            print(f"  - 文件大小: {result['file_size'] / 1024:.2f} KB")
            print(f"  - 文件格式: {result['file_ext']}")
            print(f"  - 使用的解析器: {result['parser']}")
            print(f"  - 提取的文本长度: {result['text_length']} 字符")
            print(f"  - 提取的文本预览:\n{result['text'][:200]}...")
    else:
        print(f"[INFO] 测试文件不存在: {test_file}")
        print("[INFO] 请提供一个测试文件来验证解析功能")

    print("\n" + "=" * 60)
