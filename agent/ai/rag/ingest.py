"""
文档摄取模块

把用户上传的文件转成向量并写入其专属的 Chroma collection。

流程：保存原文件 → 解析文本 → 中文友好切片 → 向量化入库
"""
import logging
import os
import shutil
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import common.vector_store as vector_store
from config import (
    ALLOWED_EXTENSIONS,
    CHUNK_OVERLAP,
    CHUNK_SEPARATORS,
    CHUNK_SIZE,
    MAX_UPLOAD_SIZE,
    UPLOAD_DIR,
)

logger = logging.getLogger(__name__)


class IngestError(ValueError):
    """文档解析失败"""


def get_splitter() -> RecursiveCharacterTextSplitter:
    """
    构建中英文混排的切片器

    分隔符按中文标点优先，尽量在句末断开而不是把句子从中间切断。
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=CHUNK_SEPARATORS,
        length_function=len,
    )


# ============== 文件保存 ==============

def get_user_upload_dir(user_id: int) -> str:
    """
    获取某个用户的上传目录

    Args:
        user_id: 用户主键

    Returns:
        目录路径（不存在则创建）
    """
    path = os.path.join(UPLOAD_DIR, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path


def validate_upload(filename: Optional[str], size: int) -> str:
    """
    校验上传文件是否合法

    Args:
        filename: 原始文件名
        size: 文件字节数

    Returns:
        规范化后的文件扩展名（如 "pdf"）

    Raises:
        IngestError: 文件名缺失、类型不支持或超出大小限制
    """
    if not filename:
        raise IngestError("未收到文件")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        supported = "、".join(sorted(ALLOWED_EXTENSIONS))
        raise IngestError(f"不支持的文件类型 {ext or '(无扩展名)'}，仅支持: {supported}")

    if size <= 0:
        raise IngestError("文件内容为空")
    if size > MAX_UPLOAD_SIZE:
        limit_mb = MAX_UPLOAD_SIZE / 1024 / 1024
        raise IngestError(f"文件超过 {limit_mb:.0f}MB 上限")

    return ext.lstrip(".")


def save_upload(user_id: int, document_id: int, filename: str, ext: str, content: bytes) -> str:
    """
    保存上传的原始文件

    Args:
        user_id: 用户主键
        document_id: 文档主键
        filename: 原始文件名
        ext: 扩展名（不含点）
        content: 文件二进制内容

    Returns:
        保存后的绝对路径
    """
    # 只取扩展名，不沿用用户提供的文件名，避免 ../ 之类的路径穿越
    safe_name = f"{document_id}.{ext}"
    target = os.path.join(get_user_upload_dir(user_id), safe_name)
    with open(target, "wb") as f:
        f.write(content)
    return target


def delete_upload(user_id: int, document_id: int, ext: str) -> None:
    """
    删除已保存的原始文件

    Args:
        user_id: 用户主键
        document_id: 文档主键
        ext: 扩展名（不含点）
    """
    target = os.path.join(get_user_upload_dir(user_id), f"{document_id}.{ext}")
    try:
        if os.path.exists(target):
            os.remove(target)
    except OSError as e:
        logger.warning(f"删除原文件失败 {target}: {e}")


def delete_user_upload_dir(user_id: int) -> None:
    """
    删除用户的整个上传目录（注销账号时调用）

    Args:
        user_id: 用户主键
    """
    path = os.path.join(UPLOAD_DIR, str(user_id))
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            logger.info(f"已删除用户 {user_id} 的上传目录")
    except OSError as e:
        logger.warning(f"删除上传目录失败 {path}: {e}")


# ============== 文本解析 ==============

def parse_txt(content: bytes) -> str:
    """
    解析纯文本 / Markdown

    依次尝试 UTF-8、GBK、UTF-16，中文环境下的 txt 常用 GBK 编码。
    """
    for encoding in ("utf-8", "gbk", "utf-16"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    # 都解不开时按 latin-1 兜底，保证不会丢内容
    return content.decode("utf-8", errors="replace")


def parse_pdf(path: str) -> List[Dict[str, Any]]:
    """
    解析 PDF

    Args:
        path: PDF 文件路径

    Returns:
        [{"page": 页码(从1开始), "text": "该页文本"}, ...]

    Raises:
        IngestError: PDF 解析失败或没有可提取的文字
    """
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise IngestError("未安装 pypdf，无法解析 PDF") from e

    try:
        reader = PdfReader(path)
    except Exception as e:
        raise IngestError(f"PDF 解析失败: {e}") from e

    pages = []
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            logger.warning(f"PDF 第 {page_no} 页提取失败，跳过: {e}")
            continue
        text = text.strip()
        if text:
            pages.append({"page": page_no, "text": text})

    if not pages:
        raise IngestError("PDF 中没有可提取的文字（可能是扫描件，暂不支持 OCR）")

    return pages


def load_text(content: bytes, ext: str, path: str) -> List[Dict[str, Any]]:
    """
    按扩展名把文件内容解析成带页码信息的文本块

    Args:
        content: 文件二进制内容
        ext: 扩展名（不含点）
        path: 已保存的文件路径（PDF 需要从路径读取）

    Returns:
        [{"page": int | None, "text": str}, ...]

    Raises:
        IngestError: 解析失败
    """
    if ext == "pdf":
        return parse_pdf(path)

    text = parse_txt(content).strip()
    if not text:
        raise IngestError("文件内容为空或只有空白字符")
    return [{"page": None, "text": text}]


# ============== 切片与入库 ==============

def split_into_chunks(
    text: str,
    user_id: int,
    document_id: int,
    filename: str,
    page: Optional[int] = None,
) -> List[Document]:
    """
    把文本切成带元数据的 LangChain Document

    元数据里的 document_id 是后续删除向量的依据，
    过滤统一用整数类型——Chroma 的 where 过滤对字段类型敏感。

    Args:
        text: 原始文本
        user_id: 用户主键
        document_id: 文档主键
        filename: 原始文件名
        page: 页码（非 PDF 为 None）

    Returns:
        Document 列表
    """
    raw_chunks = get_splitter().split_text(text)

    documents = []
    for index, content in enumerate(raw_chunks):
        cleaned = content.strip()
        if not cleaned:
            continue
        metadata: Dict[str, Any] = {
            "user_id": int(user_id),
            "document_id": int(document_id),
            "filename": filename,
            "chunk_index": len(documents),
        }
        if page is not None:
            metadata["page"] = page
        documents.append(Document(page_content=cleaned, metadata=metadata))

    return documents


def count_tokens(text: str) -> int:
    """
    估算 token 数

    中文一个字约等于 1~1.5 个 token，这里按字符数估算即可，
    只用于入库统计，不需要精确值。
    """
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return len(text)


def ingest_file(
    user_id: int,
    document_id: int,
    filename: str,
    ext: str,
    content: bytes,
) -> List[Dict[str, Any]]:
    """
    把一个上传文件完整走完「解析 → 切片 → 向量化入库」

    Args:
        user_id: 用户主键
        document_id: 文档主键
        filename: 原始文件名
        ext: 扩展名（不含点）
        content: 文件二进制内容

    Returns:
        [{"chunk_index": int, "content": str, "token_count": int}, ...]

    Raises:
        IngestError: 解析失败或未能切出任何切片
    """
    path = save_upload(user_id, document_id, filename, ext, content)
    blocks = load_text(content, ext, path)

    all_chunks: List[Dict[str, Any]] = []
    documents: List[Document] = []

    for block in blocks:
        for doc in split_into_chunks(
            text=block["text"],
            user_id=user_id,
            document_id=document_id,
            filename=filename,
            page=block.get("page"),
        ):
            documents.append(doc)
            all_chunks.append({
                "chunk_index": doc.metadata["chunk_index"],
                "content": doc.page_content,
                "token_count": count_tokens(doc.page_content),
            })

    if not documents:
        raise IngestError("未能从文件中切出有效内容")

    vector_store.add_documents(user_id, documents)
    logger.info(
        f"用户 {user_id} 的文档 {document_id} ({filename}) 入库完成: {len(documents)} 个切片"
    )

    return all_chunks