FROM python:3.12-slim

WORKDIR /app

# System deps for spaCy native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy English model (used for entity extraction + lemmatization)
RUN python -m spacy download en_core_web_sm

# Allow "sagemaker" and "tei_local" as embedding providers in mem0's config validator
RUN sed -i 's/"aws_bedrock",/"aws_bedrock", "sagemaker", "tei_local",/' \
    /usr/local/lib/python3.12/site-packages/mem0/embeddings/configs.py

# Pin ONE OpenRouter provider (no fallbacks) for extraction. mem0 @ 94c3fe9 can route to
# OpenRouter but has no config path for OpenRouter's `provider` routing object, so we inject
# it into the installed OpenAILLM.generate_response right before the create() call. Runtime-
# gated on OPENROUTER_API_KEY + OPENROUTER_PROVIDER, so the default (OpenAI/gpt-5) path is
# untouched. The anchor line is identical across the mem0 refs we build (94c3fe9 and
# code/session-date). sed cannot fail on a missing match, so grep-verify and fail the build
# loudly if the patch did not apply.
RUN F=/usr/local/lib/python3.12/site-packages/mem0/llms/openai.py && \
    sed -i '/response = self.client.chat.completions.create(\*\*params)/i\        if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_PROVIDER"):\n            params["extra_body"] = {"provider": {"only": [os.getenv("OPENROUTER_PROVIDER")], "allow_fallbacks": False}}' "$F" && \
    grep -q 'params\["extra_body"\] = {"provider": {"only": \[os.getenv("OPENROUTER_PROVIDER")\]' "$F" || \
    { echo "ERROR: OpenRouter provider-pin patch did not apply to $F (mem0 source changed?)" >&2; exit 1; }

# History directory
RUN mkdir -p /app/history

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
