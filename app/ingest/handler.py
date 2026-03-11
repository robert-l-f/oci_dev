import json
import os
from typing import Any, Dict, List

import mysql.connector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _mysql_connection():
    return mysql.connector.connect(
        host=_required_env("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=_required_env("MYSQL_USER"),
        password=_required_env("MYSQL_PASSWORD"),
        database=_required_env("MYSQL_DATABASE"),
    )


def _ensure_schema(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_chunks (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            doc_id VARCHAR(255) NOT NULL,
            chunk_index INT NOT NULL,
            content TEXT NOT NULL,
            metadata JSON NULL,
            embedding JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_doc_id (doc_id)
        )
        """
    )


def _extract_documents(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    docs = payload.get("documents")
    if docs is None and payload.get("document"):
        docs = [payload["document"]]
    if docs is None and payload.get("text"):
        docs = [{"id": payload.get("id", "manual-doc"), "text": payload["text"], "metadata": payload.get("metadata", {})}]

    if not docs or not isinstance(docs, list):
        raise ValueError("Payload must include 'documents' (list), 'document', or 'text'.")

    normalized = []
    for i, doc in enumerate(docs):
        if not isinstance(doc, dict):
            raise ValueError(f"Document at index {i} must be an object.")
        text = str(doc.get("text", "")).strip()
        if not text:
            continue
        normalized.append(
            {
                "id": str(doc.get("id") or f"doc-{i}"),
                "text": text,
                "metadata": doc.get("metadata", {}),
            }
        )
    if not normalized:
        raise ValueError("No valid documents with non-empty 'text' were provided.")
    return normalized


def handler(ctx, data: bytes = None):
    conn = None
    cursor = None
    try:
        body = json.loads((data or b"{}").decode("utf-8"))
        docs = _extract_documents(body)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("CHUNK_SIZE", "800")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "120")),
        )
        embedder = OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))

        conn = _mysql_connection()
        cursor = conn.cursor()
        _ensure_schema(cursor)

        replace_existing = os.getenv("REPLACE_EXISTING_DOC", "true").lower() == "true"
        inserted = 0
        per_doc = []

        for doc in docs:
            doc_id = doc["id"]
            chunks = splitter.split_text(doc["text"])
            if not chunks:
                per_doc.append({"doc_id": doc_id, "chunks_inserted": 0})
                continue

            if replace_existing:
                cursor.execute("DELETE FROM rag_chunks WHERE doc_id = %s", (doc_id,))

            vectors = embedder.embed_documents(chunks)
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
                cursor.execute(
                    """
                    INSERT INTO rag_chunks (doc_id, chunk_index, content, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (doc_id, idx, chunk, json.dumps(doc["metadata"]), json.dumps(vector)),
                )
                inserted += 1

            per_doc.append({"doc_id": doc_id, "chunks_inserted": len(chunks)})

        conn.commit()
        return json.dumps(
            {
                "status": "ingested",
                "documents": len(docs),
                "chunks_inserted": inserted,
                "results": per_doc,
            }
        )
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        return json.dumps({"error": str(exc)})
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
