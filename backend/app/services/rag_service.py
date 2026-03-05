"""
RAG 服务 - 兽医知识库检索引擎
- 启动时加载 knowledge_base/*.md 到 ChromaDB
- 提供基于症状文本的 Top-K 文档检索
- Embedding: google-generativeai (text-embedding-004)
"""
from __future__ import annotations
from typing import Optional, List
import os
import glob
import hashlib
import logging
from pathlib import Path

import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from google import genai
from google.genai import types
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_NAME = "petafu_vet_knowledge"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


class GeminiEmbeddingFunction(EmbeddingFunction):
    """使用 Gemini text-embedding-004 作为向量化函数"""

    def __init__(self, api_key: str):
        self._client = genai.Client(api_key=api_key)

    def __call__(self, input: Documents) -> Embeddings:
        results = []
        for text in input:
            r = self._client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
            )
            results.append(r.embeddings[0].values)
        return results


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """简单滑动窗口切块"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


class RAGService:
    def __init__(self):
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection = None
        self._initialized = False

    def _get_client(self):
        if self._client is None:
            persist_dir = settings.chroma_persist_dir
            os.makedirs(persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_dir)
        return self._client

    def _get_collection(self):
        if self._collection is None:
            embedding_fn = GeminiEmbeddingFunction(api_key=settings.openai_api_key)
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def build_index(self) -> int:
        """
        扫描 knowledge_base 目录，将所有 .md 文件切块后存入 ChromaDB。
        返回本次新增的 chunk 数量，已索引文件通过内容 hash 去重。
        """
        collection = self._get_collection()
        kb_dir = Path(settings.knowledge_base_dir)
        if not kb_dir.exists():
            logger.warning(f"knowledge_base 目录不存在: {kb_dir.resolve()}")
            return 0

        existing_ids = set(collection.get(include=[])["ids"])
        logger.info(f"ChromaDB 现有 {len(existing_ids)} 个分块")

        new_count = 0
        for fpath in glob.glob(str(kb_dir / "**/*.md"), recursive=True):
            fname = Path(fpath).name
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            chunks = _chunk_text(content)
            for i, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{fname}_{i}_{chunk[:50]}".encode()).hexdigest()
                if chunk_id in existing_ids:
                    continue
                collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[{"source": fname, "chunk_index": i}],
                )
                new_count += 1

        logger.info(f"RAG 索引完成，新增 {new_count} 个分块")
        self._initialized = True
        return new_count

    def retrieve(self, query: str, top_k: int = 3) -> str:
        """
        基于症状文本查询最相关的兽医文献片段
        返回拼接好的上下文字符串，可直接注入 Prompt
        """
        collection = self._get_collection()
        count = collection.count()
        if count == 0:
            logger.warning("知识库为空，跳过 RAG 检索")
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        context_parts = []
        for doc, meta in zip(docs, metas):
            source = meta.get("source", "未知来源")
            context_parts.append(f"【来源：{source}】\n{doc.strip()}")

        return "\n\n".join(context_parts)


# 单例
rag_service = RAGService()
