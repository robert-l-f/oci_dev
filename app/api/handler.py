import json
import math
import os
from typing import Dict, List, Tuple

import mysql.connector
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


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


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _retrieve(question_embedding: List[float], limit: int, candidate_pool: int) -> List[Tuple[float, str, str]]:
    conn = _mysql_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT doc_id, content, embedding
            FROM rag_chunks
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (candidate_pool,),
        )

        scored = []
        for doc_id, content, embedding_json in cursor.fetchall():
            emb = embedding_json if isinstance(embedding_json, list) else json.loads(embedding_json)
            score = _cosine_similarity(question_embedding, emb)
            scored.append((score, doc_id, content))

        scored.sort(key=lambda row: row[0], reverse=True)
        return scored[:limit]
    finally:
        cursor.close()
        conn.close()


def _build_prompt(question: str, matches: List[Tuple[float, str, str]]) -> str:
    context = "\n\n".join([f"[doc={doc_id} score={score:.3f}]\n{content}" for score, doc_id, content in matches])
    if not context:
        context = "No context chunks were retrieved."
    return (
        "You are a retrieval-augmented assistant. Use only the provided context. "
        "If context is missing or insufficient, state that clearly.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    )


def handler(ctx, data: bytes = None):
    try:
        body: Dict = json.loads((data or b"{}").decode("utf-8"))
        question = str(body.get("question", "")).strip()
        if not question:
            return json.dumps({"error": "Request must include a non-empty 'question'."})

        top_k = max(1, min(int(body.get("top_k", os.getenv("TOP_K", "4"))), 20))
        candidate_pool = max(top_k, int(body.get("candidate_pool", os.getenv("CANDIDATE_POOL", "200"))))

        embedder = OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
        q_emb = embedder.embed_query(question)

        matches = _retrieve(q_emb, limit=top_k, candidate_pool=candidate_pool)
        prompt = _build_prompt(question, matches)

        response_payload = {
            "question": question,
            "retrieved": len(matches),
            "matches": [
                {"score": round(score, 6), "doc_id": doc_id, "content": content}
                for score, doc_id, content in matches
            ],
        }

        if os.getenv("OPENAI_API_KEY"):
            chat = ChatOpenAI(model=os.getenv("CHAT_MODEL", "gpt-4o-mini"), temperature=0)
            response_payload["answer"] = chat.invoke(prompt).content
        else:
            response_payload["answer"] = "OPENAI_API_KEY is not configured; returning retrieval results only."

        return json.dumps(response_payload)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
