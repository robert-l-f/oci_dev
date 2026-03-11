# OCI + MySQL HeatWave GenAI RAG Starter

This repository now includes a working starter implementation for the architecture in Oracle's guide:
**Build a RAG system with LangChain and MySQL HeatWave GenAI**.

## What is included

- **`app/ingest`**: OCI Function that chunks source text and stores embeddings in MySQL.
- **`app/api`**: OCI Function that embeds a question, retrieves similar chunks, and generates an answer.
- **`app/dashboard`**: Streamlit stub app (optional UI layer).
- **`terraform`**: existing infrastructure scaffold for OCI resources.

## Flow

1. Send documents to **ingest** function (`/documents` or similar endpoint through API Gateway).
2. The function splits text into chunks with `RecursiveCharacterTextSplitter`.
3. Embeddings are generated with `OpenAIEmbeddings` and stored in `rag_chunks`.
4. Send a user question to **api** function.
5. The API function embeds the question, ranks stored chunks by cosine similarity, and sends context to `ChatOpenAI`. Ingest can replace existing chunks per `doc_id` to keep updates idempotent.

## Environment variables

Set these for both `app/ingest` and `app/api`:

```bash
MYSQL_HOST=<heatwave_or_mysql_host>
MYSQL_PORT=3306
MYSQL_USER=<user>
MYSQL_PASSWORD=<password>
MYSQL_DATABASE=<database>
OPENAI_API_KEY=<api_key>
EMBEDDING_MODEL=text-embedding-3-small
```

Optional:

```bash
CHUNK_SIZE=800
CHUNK_OVERLAP=120
TOP_K=4
CHAT_MODEL=gpt-4o-mini
CANDIDATE_POOL=200
REPLACE_EXISTING_DOC=true
```

## MySQL table

`app/ingest` creates this table automatically if it does not exist:

```sql
CREATE TABLE rag_chunks (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  doc_id VARCHAR(255) NOT NULL,
  chunk_index INT NOT NULL,
  content TEXT NOT NULL,
  metadata JSON NULL,
  embedding JSON NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_doc_id (doc_id)
);
```

## Example payloads

### Ingest

```json
{
  "documents": [
    {
      "id": "employee-handbook-v1",
      "text": "Long source content...",
      "metadata": {
        "source": "hr",
        "lang": "en"
      }
    }
  ]
}
```

### Query

```json
{
  "question": "What is the remote work policy?",
  "top_k": 4
}
```

## Deploying OCI Functions

From each function folder (`app/ingest` and `app/api`):

```bash
fn build
fn deploy --app <oci-fn-app-name>
```

Then configure environment variables in OCI Functions config (or via `fn config function`).

## Notes for production hardening

- Move embeddings and generation to **OCI Generative AI** or HeatWave-native embedding functions if required by policy.
- Replace JSON embedding storage with HeatWave vector-native indexing where available.
- Add authn/authz (IAM, JWT, or API Gateway policies).
- Add retries, dead-letter handling, and ingestion idempotency.
- Add observability (OCI Logging/Monitoring, traces, request IDs).
