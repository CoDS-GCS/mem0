#!/usr/bin/env python3
"""
serve_qwen_tei.py — local Qwen3-Embedding-0.6B service with a TEI-compatible API.

Why this exists: Mem0's published LongMemEval OSS table uses "Qwen 600M via SageMaker"
(memory-benchmarks/README.md:242) behind a HuggingFace TEI endpoint. TEI in Docker can't
run on this box (no nvidia Docker runtime + full root disk), so we serve the *same model*
as a host process on the GPU and expose the *same wire contract* TEI uses, so only the
transport changes. Our Mem0 embedder (docker/mem0/tei_local_embedder.py) posts here exactly
as SageMakerEmbedding posts to SageMaker.

Math matches the Qwen3-Embedding-0.6B model card recipe (and therefore TEI's):
  - left padding, last-token pooling (take the final non-pad token's hidden state),
  - L2-normalize the FULL vector,
  - fp16 on GPU, no instruction prefix (the client sends none; add and search are identical).
The client truncates to the first `embedding_dims` dims itself (Matryoshka), with no
re-normalization — exactly like SageMakerEmbedding `[: self.dims]`.

API (TEI-compatible):
  POST /embed        {"inputs": ["a", "b"]}  -> [[...], [...]]   (list of float lists)
  POST /embeddings   alias of /embed
  GET  /health       -> {"status": "ok", ...}
  GET  /info         -> model id, revision, dims, device, dtype, pooling, normalize

Env:
  QWEN_MODEL_ID        default Qwen/Qwen3-Embedding-0.6B
  QWEN_MODEL_REVISION  pinned HF commit (default below)
  QWEN_DEVICE          cuda | cpu  (default: cuda if available)
  QWEN_MAX_TOKENS      max sequence length (default 512)
  EMBED_PORT/EMBED_HOST are handled by run_embedding_service.sh, not here.
"""

from __future__ import annotations

import os
from typing import List

import torch
import torch.nn.functional as F
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer

MODEL_ID = os.getenv("QWEN_MODEL_ID", "Qwen/Qwen3-Embedding-0.6B")
# Pinned revision of Qwen/Qwen3-Embedding-0.6B (native 1024 dims; last-token pooling).
MODEL_REVISION = os.getenv("QWEN_MODEL_REVISION", "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3")
MAX_TOKENS = int(os.getenv("QWEN_MAX_TOKENS", "512"))
DEVICE = os.getenv("QWEN_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
DTYPE = torch.float16 if DEVICE.startswith("cuda") else torch.float32

app = FastAPI(title="Qwen3-Embedding-0.6B (TEI-compatible)", docs_url=None, redoc_url=None)

_STATE: dict = {"model": None, "tokenizer": None, "native_dims": None}


def _load():
    if _STATE["model"] is not None:
        return
    tok = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, padding_side="left")
    model = AutoModel.from_pretrained(MODEL_ID, revision=MODEL_REVISION, torch_dtype=DTYPE)
    model.eval().to(DEVICE)
    _STATE["tokenizer"] = tok
    _STATE["model"] = model
    _STATE["native_dims"] = int(model.config.hidden_size)


def _last_token_pool(last_hidden: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """Last-token pooling that is correct for both left- and right-padding (model card recipe)."""
    left_padded = attention_mask[:, -1].sum() == attention_mask.shape[0]
    if left_padded:
        return last_hidden[:, -1]
    seq_len = attention_mask.sum(dim=1) - 1
    return last_hidden[torch.arange(last_hidden.shape[0], device=last_hidden.device), seq_len]


@torch.inference_mode()
def embed_texts(texts: List[str]) -> List[List[float]]:
    _load()
    tok, model = _STATE["tokenizer"], _STATE["model"]
    batch = tok(texts, padding=True, truncation=True, max_length=MAX_TOKENS, return_tensors="pt").to(DEVICE)
    out = model(**batch)
    pooled = _last_token_pool(out.last_hidden_state, batch["attention_mask"])
    pooled = F.normalize(pooled, p=2, dim=1)          # L2-normalize the FULL native vector
    return pooled.to(torch.float32).cpu().tolist()


class EmbedRequest(BaseModel):
    inputs: list


@app.on_event("startup")
def _startup():
    _load()


@app.get("/health")
def health():
    return {"status": "ok" if _STATE["model"] is not None else "loading",
            "model": MODEL_ID, "revision": MODEL_REVISION, "device": DEVICE}


@app.get("/info")
def info():
    _load()
    return {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "native_dims": _STATE["native_dims"],
        "device": DEVICE,
        "dtype": str(DTYPE).replace("torch.", ""),
        "pooling": "last_token",
        "padding_side": "left",
        "normalize": "l2_full_vector",
        "instruction": "none",
        "max_tokens": MAX_TOKENS,
    }


def _coerce_inputs(inputs) -> List[str]:
    if isinstance(inputs, str):
        return [inputs]
    return [str(x) for x in inputs]


@app.post("/embed")
def embed(req: EmbedRequest):
    return embed_texts(_coerce_inputs(req.inputs))


@app.post("/embeddings")
def embeddings(req: EmbedRequest):
    return embed_texts(_coerce_inputs(req.inputs))
