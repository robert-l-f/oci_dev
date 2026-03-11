# Build and Run an OCI RAG Stack (Step-by-Step Tutorial)

This is a **start-to-finish tutorial** for deploying and using a Retrieval-Augmented Generation (RAG) system on Oracle Cloud Infrastructure (OCI) with:

- OCI Functions (`app/ingest`, `app/api`)
- MySQL HeatWave (stores chunks + embeddings)
- Terraform (minimum OCI network + Functions app resources)
- Optional Streamlit dashboard (`app/dashboard`)

If you follow the steps in order, you should end with a working stack that can ingest text and answer questions from that text.

---

## What you are building

You will deploy two serverless functions:

1. **Ingest function**: accepts documents, chunks text, generates embeddings, and writes rows to MySQL.
2. **API function**: accepts a question, embeds it, retrieves similar chunks, and returns an answer grounded in retrieved content.

---

## Repository layout

- `app/ingest` – OCI Function for ingestion
- `app/api` – OCI Function for Q&A retrieval/generation
- `app/dashboard` – optional Streamlit UI to call the API function
- `terraform/` – minimum infrastructure to host OCI Functions in private subnet

---

## Step 0: Prerequisites

Have these ready before you start:

- OCI tenancy + compartment you can deploy into
- OCI CLI installed and authenticated (`oci setup config` completed)
- Terraform >= 1.5
- Docker installed/running
- Fn CLI installed (`fn version` works)
- Access to OCIR (Oracle Container Registry)
- Existing MySQL HeatWave instance and database credentials
- OpenAI API key

Useful checks:

```bash
oci --version
terraform version
docker --version
fn version
```

---

## Step 1: Clone and enter the repo

```bash
git clone <your-repo-url>
cd oci_dev
```

---

## Step 2: Configure Terraform variables

Open `terraform/terraform.tfvars` and set:

```hcl
region           = "us-ashburn-1"
compartment_ocid = "ocid1.compartment.oc1..replace_me"
project_name     = "rag-stack"
```

You can also customize optional CIDRs/DNS labels in `terraform/variables.tf` defaults if needed.

---

## Step 3: Deploy minimum OCI infrastructure

The Terraform stack creates:

- VCN
- Private subnet for Functions
- NAT Gateway + Service Gateway
- Route table and security list for egress
- OCI Functions Application

Run:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Capture outputs for later:

```bash
terraform output functions_application_name
terraform output functions_application_id
terraform output functions_subnet_id
terraform output vcn_id
```

---

## Step 4: Configure Fn context

Set Fn context values for your tenancy/region/registry.

```bash
fn update context oracle.compartment-id <compartment_ocid>
fn update context api-url https://functions.<region>.oci.oraclecloud.com
fn update context registry <region>.ocir.io/<tenancy-namespace>/<repo>
```

Use `functions_application_name` from Terraform outputs as your function app name (`<fn_app_name>`).

---

## Step 5: Build and deploy the ingest function

```bash
cd ../app/ingest
fn -v deploy --app <fn_app_name>
```

---

## Step 6: Build and deploy the api function

```bash
cd ../api
fn -v deploy --app <fn_app_name>
```

List functions and verify both are present:

```bash
fn list functions <fn_app_name>
```

---

## Step 7: Configure runtime environment variables

Set these on **both** functions (`ingest` and `api`):

```bash
# ingest
fn config function <fn_app_name> ingest MYSQL_HOST <mysql_host>
fn config function <fn_app_name> ingest MYSQL_PORT 3306
fn config function <fn_app_name> ingest MYSQL_USER <mysql_user>
fn config function <fn_app_name> ingest MYSQL_PASSWORD <mysql_password>
fn config function <fn_app_name> ingest MYSQL_DATABASE <mysql_database>
fn config function <fn_app_name> ingest OPENAI_API_KEY <openai_api_key>
fn config function <fn_app_name> ingest EMBEDDING_MODEL text-embedding-3-small

# api
fn config function <fn_app_name> api MYSQL_HOST <mysql_host>
fn config function <fn_app_name> api MYSQL_PORT 3306
fn config function <fn_app_name> api MYSQL_USER <mysql_user>
fn config function <fn_app_name> api MYSQL_PASSWORD <mysql_password>
fn config function <fn_app_name> api MYSQL_DATABASE <mysql_database>
fn config function <fn_app_name> api OPENAI_API_KEY <openai_api_key>
fn config function <fn_app_name> api EMBEDDING_MODEL text-embedding-3-small
```

Optional tuning:

```bash
# ingest tuning
fn config function <fn_app_name> ingest CHUNK_SIZE 800
fn config function <fn_app_name> ingest CHUNK_OVERLAP 120
fn config function <fn_app_name> ingest REPLACE_EXISTING_DOC true

# api tuning
fn config function <fn_app_name> api TOP_K 4
fn config function <fn_app_name> api CANDIDATE_POOL 200
fn config function <fn_app_name> api CHAT_MODEL gpt-4o-mini
```

---

## Step 8: Ingest your first document

Create payload:

```bash
cat <<'JSON' > ingest.json
{
  "documents": [
    {
      "id": "policy-remote-work-v1",
      "text": "Employees may work remotely up to 3 days per week with manager approval.",
      "metadata": {"source": "hr-policy"}
    }
  ]
}
JSON
```

Invoke ingest:

```bash
fn invoke <fn_app_name> ingest < ingest.json
```

Expected: JSON response showing `status: ingested` and `chunks_inserted` > 0.

---

## Step 9: Ask your first question

Create query payload:

```bash
cat <<'JSON' > ask.json
{
  "question": "How many remote days are allowed?",
  "top_k": 4
}
JSON
```

Invoke API:

```bash
fn invoke <fn_app_name> api < ask.json
```

Expected: JSON with retrieved matches and an `answer` field.

---

## Step 10: (Optional) Run the dashboard locally

```bash
cd ../dashboard
RAG_API_URL=<api-function-http-endpoint> streamlit run handler.py
```

Use the browser UI to send questions and inspect raw API responses.

---

## Step 11: Validate data landed in MySQL

The ingest function creates this table automatically if missing:

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

Quick checks:

```sql
SELECT COUNT(*) FROM rag_chunks;
SELECT doc_id, chunk_index, LEFT(content, 120) FROM rag_chunks ORDER BY created_at DESC LIMIT 10;
```

---

## Troubleshooting

### `Missing required environment variable`
Set all required `MYSQL_*` and `OPENAI_API_KEY` values on both functions and redeploy/invoke again.

### `fn deploy` fails on registry/auth
Verify OCIR auth, `fn` context registry value, and your Docker login to OCIR.

### API returns retrieval but weak answer
Increase `CANDIDATE_POOL`, tune `TOP_K`, and ingest richer source content.

### No chunks inserted
Check input payload shape (`documents` list with `text`), and confirm text is non-empty.

---

## Production hardening (next steps)

- Move secrets to OCI Vault / Secret integration.
- Add API Gateway + IAM/JWT auth in front of functions.
- Add structured logging + tracing + metrics.
- Use vector-native storage/indexing in HeatWave where available.
- Add CI/CD pipeline for `terraform plan/apply` and function deployment.

---

## One-command reminder of run order

1. Configure `terraform/terraform.tfvars`
2. `terraform init && terraform apply`
3. Set `fn` context
4. `fn deploy` for `ingest` and `api`
5. Set function env vars
6. Invoke `ingest`
7. Invoke `api`
8. (Optional) run dashboard

That is the full end-to-end workflow.
