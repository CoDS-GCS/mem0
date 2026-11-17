"""
Local TEI Embedding Provider
============================

Identical in behaviour to SageMakerEmbedding (docker/mem0/sagemaker_embedder.py) — same
request payload, same response parsing, same Matryoshka ``[: self.dims]`` truncation with no
re-normalization, same "memory_action is accepted but ignored" semantics (add and search
embed identically, no instruction prefix). The ONLY difference is transport: it POSTs to a
local HuggingFace TEI-compatible endpoint over HTTP instead of AWS SageMaker.

This serves Mem0's published "Qwen 600M via SageMaker" embedder (README.md:242) on hardware
where TEI-in-Docker can't run. It is enabled only when EMBEDDER_PROVIDER=tei_local, so the
default server, all LoCoMo runs and trace_view.py are unchanged.

Endpoint contract (see experiments/embedding_service/serve_qwen_tei.py):
  POST <url>   {"inputs": [text, ...]}  ->  [[float, ...], ...]

Config / env:
  TEI_LOCAL_URL         full embed URL, e.g. http://host.docker.internal:8099/embed
  embedding_dims        truncation length (config.embedding_dims; default 768 to match
                        SageMakerEmbedding's default)
"""

import json
import logging
import os
import urllib.request
from typing import Literal, Optional

from mem0.configs.embeddings.base import BaseEmbedderConfig
from mem0.embeddings.base import EmbeddingBase

logger = logging.getLogger(__name__)


class TEILocalEmbedding(EmbeddingBase):

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)
        # URL comes from env (BaseEmbedderConfig rejects unknown keys, exactly like the
        # SageMaker provider reading SAGEMAKER_ENDPOINT_NAME from env).
        self.url = os.getenv("TEI_LOCAL_URL", "http://host.docker.internal:8099/embed")
        self.dims = self.config.embedding_dims or 768
        self.timeout = float(os.getenv("TEI_LOCAL_TIMEOUT", "60"))
        logger.info("TEI-local embedder: url=%s, dims=%d", self.url, self.dims)

    def _post(self, inputs: list[str]) -> list[list[float]]:
        body = json.dumps({"inputs": inputs}).encode("utf-8")
        req = urllib.request.Request(self.url, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def embed(self, text: str, memory_action: Optional[Literal["add", "search", "update"]] = None) -> list[float]:
        text = text.replace("\n", " ")
        result = self._post([text])
        return result[0][: self.dims]

    def embed_batch(self, texts: list[str], memory_action: str = "add") -> list[list[float]]:
        texts = [t.replace("\n", " ") for t in texts]
        result = self._post(texts)
        return [vec[: self.dims] for vec in result]
