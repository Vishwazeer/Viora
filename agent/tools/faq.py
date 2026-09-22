"""
Viora – FAQ Tool.
Semantic similarity search over clinic FAQ entries.
Uses simple cosine similarity on TF-IDF vectors (no external embedding API needed).
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"


def _load_faq() -> list[dict]:
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("faq", [])


def _tokenise(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", "", text.lower()).split()


def _tf_idf_vector(tokens: list[str], vocab: set[str]) -> dict[str, float]:
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    total = max(len(tokens), 1)
    return {t: (tf.get(t, 0) / total) for t in vocab}


def _cosine(a: dict[str, float], b: dict[str, float], vocab: set[str]) -> float:
    dot = sum(a.get(t, 0) * b.get(t, 0) for t in vocab)
    mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class FAQEngine:
    def __init__(self) -> None:
        self._faq = _load_faq()
        self._indexed = [(entry, _tokenise(entry["question"])) for entry in self._faq]

    def search(self, query: str, threshold: float = 0.15) -> dict | None:
        query_tokens = _tokenise(query)
        vocab = set(query_tokens)
        for _, tokens in self._indexed:
            vocab |= set(tokens)

        query_vec = _tf_idf_vector(query_tokens, vocab)
        best_score = 0.0
        best_entry: dict | None = None

        for entry, tokens in self._indexed:
            entry_vec = _tf_idf_vector(tokens, vocab)
            score = _cosine(query_vec, entry_vec, vocab)
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_score >= threshold and best_entry:
            return {"found": True, "answer": best_entry["answer"], "score": round(best_score, 3)}
        return {"found": False}


_engine = FAQEngine()


async def search_faq(query: str) -> dict:
    """Tool entry-point: search FAQ for the caller's query."""
    return _engine.search(query)
