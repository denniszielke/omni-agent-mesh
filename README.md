# omni-agent-mesh

## Requirements

- AI Foundry with model deployments
- Azure AI Search service
- Python 3.11+
- `git` and `virtualenv` (or `python -m venv`)

## 1. Python virtual environment

From the repo root (`agentic-investigators`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Deploy infra as code using azd

The following lines of code will connect your Codespace az cli and azd cli to the right Azure subscription:
```
azd up
```
Get the values for some env variables

get and set the value for AZURE_ENV_NAME
```
source <(azd env get-values | grep AZURE_ENV_NAME)

echo "building and deploying the work_env_agent agents"
bash ./azd-hooks/deploy.sh work_env_agent $AZURE_ENV_NAME


echo "building and deploying the intranet_agent agents"
bash ./azd-hooks/deploy.sh intranet_agent $AZURE_ENV_NAME

echo "building and deploying the intranet mcp server"
bash ./azd-hooks/deploy-mcp.sh 05-intranet-server $AZURE_ENV_NAME
```

## 3. Configure environment (`.env`)

! Only required if you did not use azd
Create a `.env` file in the repo root based on `.env.example`:

```bash
cp .env.example .env
```

Then edit `.env` and set the following values for your Azure resources (these names match `_env.example`):

- **Azure OpenAI**
	- `AZURE_OPENAI_ENDPOINT` – e.g. `https://<your-openai>.openai.azure.com`.
	- `AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME` – small chat model deployment (e.g. `gpt-4.1-mini`).
	- `AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME` – larger chat model deployment (e.g. `gpt-5.1-chat`).
	- `AZURE_OPENAI_API_KEY` – API key (leave empty if using managed identity only).
	- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME` – embedding deployment name, e.g. `text-embedding-3-small`.
	- `AZURE_OPENAI_EMBEDDING_DIMENSIONS` – embedding vector size, e.g. `1536`.
	- `AZURE_OPENAI_API_VERSION` – API version, e.g. `2024-10-21`.

- **Azure AI Search**
	- `AZURE_AI_SEARCH_ENDPOINT` – e.g. `https://<your-search>.search.windows.net`.
	- `AZURE_AI_SEARCH_KEY` – admin key for the search service (or leave empty to use `DefaultAzureCredential`).
	- `AZURE_AI_SEARCH_INDEX_NAME` – name of the index for query samples (default: `queries-index`).


Observability variables in `.env.example` are optional and can normally stay commented out for local dev.

## 4. Populate Azure AI Search index from sample queries

The file `src/ingestion/query-samples.json` contains example queries that will be indexed in Azure AI Search. To create/populate the index:

1. Ensure `.env` has valid **Azure OpenAI** and **Azure AI Search** settings (see above).
2. Activate your virtual environment.
3. From the repo root, run the ingestion script:

```bash
cd /src/ingestion
python search-index-pipeline.py
```

This will:

- Create the index (if it does not exist) with vector search enabled.
- Read all entries from `src/ingestion/query-samples.json`.
- Call the Azure OpenAI embedding deployment to create `intent_vector` values.
- Upload the documents into the configured search index.

If you see errors, verify:

- `AZURE_SEARCH_SERVICE_ENDPOINT` and `AZURE_SEARCH_ADMIN_KEY` are correct.
- The Azure OpenAI embedding deployment name, endpoint, and API version are valid.

## 5. Run the workflow locally with DevUI

The  multi‑agent workflow (including DevUI) is defined in `src/workflows/workflow.py`.

1. Make sure `.env` contains working **Azure OpenAI**, **Azure AI Search**.
2. Activate your virtual environment.
3. Start the workflow from the repo root (or the `src/workflows` folder):

```bash
cd src
python -m workflows.workflow
```

The DevUI will:

- Start a local server on `http://localhost:8093`.
- Automatically open your browser (if supported) with the workflow UI.

From there you can:

- Enter natural‑language questions.
- Let the agents search for similar queries in Azure AI Search.
