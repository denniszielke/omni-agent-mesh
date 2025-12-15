# Minimal image for running the workflow DevUI
# Uses Python 3.12, matching the project requirement
FROM python:3.12-slim

# Install system dependencies (if any future libs need them)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy dependency manifest and install dependencies first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy only the workflow code (and its local dependencies)
COPY src/workflows ./src/workflows

# Expose DevUI port
EXPOSE 8093

# Environment variables are expected to be provided at runtime, e.g.:
#   AZURE_OPENAI_ENDPOINT
#   AZURE_OPENAI_API_KEY
#   AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME
#   AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME
#   AZURE_OPENAI_EMBEDDING_MODEL
#   AZURE_OPENAI_VERSION
#   AZURE_AI_SEARCH_ENDPOINT
#   AZURE_AI_SEARCH_KEY
#   AZURE_AI_SEARCH_INDEX_NAME

ENV HOST="0.0.0.0"
ENV PORT="8093"
ENV AUTO_OPEN="False"
ENV MODE="user"

# Default command: start the workflow DevUI
CMD ["python", "src/workflows/workflow.py"]
