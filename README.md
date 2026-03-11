# OCI RAG Stack (MySQL HeatWave + OCI Functions)

This repository is now purpose-built for **one project only**: deploy and run a minimal Retrieval-Augmented Generation (RAG) stack on OCI using:

- **MySQL HeatWave** (vector storage in table JSON for starter workflow)
- **OCI Functions** for ingest and question answering
- **Terraform** for the minimum OCI network + Functions application resources
- Optional **Streamlit dashboard** for manual testing

---

## 1) Architecture

1. `app/ingest` OCI Function receives documents.
2. It chunks text with LangChain and writes chunk + embedding rows into MySQL.
3. `app/api` OCI Function receives user question.
4. It embeds the question, retrieves most similar chunks, and generates grounded answer with OpenAI chat model.
5. Optional `app/dashboard` calls the API function.

---

## 2) Prerequisites

- OCI tenancy + compartment
- OCI CLI authenticated (`oci setup config`)
- Terraform >= 1.5
- Docker
- Fn CLI (`fn version`)
- Existing MySQL HeatWave instance and database/schema credentials
- OpenAI API key

---

## 3) Deploy minimum OCI resources with Terraform

The Terraform in `terraform/` deploys only what is required to host OCI Functions in a private subnet:

- VCN
- Private subnet for Functions
- NAT Gateway + Service Gateway + route table
- Security list for egress
- OCI Functions Application

### Configure variables

Edit `terraform/terraform.tfvars`:

```hcl
region           = "us-ashburn-1"
compartment_ocid = "ocid1.compartment.oc1..replace_me"
project_name     = "rag-stack"
```

### Apply

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Capture output values:

```bash
terraform output functions_application_name
terraform output functions_application_id
```

---

## 4) Configure Fn context for OCI Functions

Set your Fn context to your compartment/subnet/registry as appropriate for your tenancy:

```bash
fn update context oracle.compartment-id <compartment_ocid>
fn update context api-url https://functions.<region>.oci.oraclecloud.com
fn update context registry <region>.ocir.io/<tenancy-namespace>/<repo>
```

Use the Terraform output name as `<fn_app_name>`.

---

## 5) Deploy functions

Deploy each function from its folder:

```bash
cd app/ingest
fn -v deploy --app <fn_app_name>

cd ../api
fn -v deploy --app <fn_app_name>
```

Get invoke endpoints:

```bash
fn list functions <fn_app_name>
```

---

## 6) Configure function environment variables

Set the same DB + embedding env vars for both `ingest` and `api` functions:

```bash
fn config function <fn_app_name> ingest MYSQL_HOST <mysql_host>
fn config function <fn_app_name> ingest MYSQL_PORT 3306
fn config function <fn_app_name> ingest MYSQL_USER <mysql_user>
fn config function <fn_app_name> ingest MYSQL_PASSWORD <mysql_password>
fn config function <fn_app_name> ingest MYSQL_DATABASE <mysql_database>
fn config function <fn_app_name> ingest OPENAI_API_KEY <openai_api_key>
fn config function <fn_app_name> ingest EMBEDDING_MODEL text-embedding-3-small

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
fn config function <fn_app_name> ingest CHUNK_SIZE 800
fn config function <fn_app_name> ingest CHUNK_OVERLAP 120
fn config function <fn_app_name> ingest REPLACE_EXISTING_DOC true

fn config function <fn_app_name> api TOP_K 4
fn config function <fn_app_name> api CANDIDATE_POOL 200
fn config function <fn_app_name> api CHAT_MODEL gpt-4o-mini
```

---

## 7) Use the stack

### Ingest sample content

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

fn invoke <fn_app_name> ingest < ingest.json
```

### Ask a question

```bash
cat <<'JSON' > ask.json
{
  "question": "How many remote days are allowed?",
  "top_k": 4
}
JSON

fn invoke <fn_app_name> api < ask.json
```

---

## 8) Optional dashboard

Run locally:

```bash
cd app/dashboard
RAG_API_URL=<api-function-http-endpoint> streamlit run handler.py
```

---

## 9) Data model created by ingest function

`app/ingest` auto-creates:

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

---

## 10) Notes for production hardening

- Use OCI Vault/Secrets for credentials.
- Move from JSON embeddings to HeatWave vector-native type/indexing where available.
- Put API Gateway + IAM auth in front of functions.
- Add retry/dead-letter workflows for ingestion.
- Add metrics, traces, and structured logs.
