from __future__ import annotations

from types import MethodType
from typing import Any


class LocalReranker:
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        batch_size: int = 16,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: Any | None = None
        self._available = False
        self._load_error: str | None = None
        self._load_model()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not documents:
            return []

        if not self._available or self._model is None:
            return self._fallback(documents, top_k=top_k)

        pairs = [(query, _document_text(document)) for document in documents]
        try:
            scores = self._model.compute_score(pairs, batch_size=self.batch_size)
        except TypeError:
            scores = self._model.compute_score(pairs)
        except Exception:
            return self._fallback(documents, top_k=top_k)

        if not isinstance(scores, list):
            try:
                scores = scores.tolist()
            except AttributeError:
                scores = [scores]

        reranked = []
        for document, score in zip(documents, scores):
            item = dict(document)
            item["rerank_score"] = float(score)
            item["rank_stage"] = "reranked"
            reranked.append(item)

        reranked.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
        return reranked[:top_k]

    def _load_model(self) -> None:
        try:
            from FlagEmbedding import FlagReranker
        except ImportError as exc:
            self._load_error = f"FlagEmbedding unavailable: {exc}"
            return

        try:
            self._model = FlagReranker(self.model_name, use_fp16=False)
            _patch_prepare_for_model(self._model)
            self._available = True
        except Exception as exc:
            self._load_error = f"Reranker load failed: {type(exc).__name__}: {exc}"

    def _fallback(
        self,
        documents: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        fallback = []
        for document in documents:
            item = dict(document)
            item["rerank_score"] = float(item.get("score", 0.0) or 0.0)
            item["rank_stage"] = "vector_fallback"
            fallback.append(item)

        fallback.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return fallback[:top_k]


def _document_text(document: dict[str, Any]) -> str:
    title = str(document.get("title") or "").strip()
    content = str(document.get("content") or "").strip()
    return "\n".join(part for part in (title, content) if part)


def _patch_prepare_for_model(model: Any) -> None:
    tokenizer = getattr(model, "tokenizer", None)
    if tokenizer is None or hasattr(tokenizer, "prepare_for_model"):
        return

    def prepare_for_model(
        self: Any,
        ids: list[int],
        pair_ids: list[int] | None = None,
        truncation: str | bool = "only_second",
        max_length: int | None = None,
        padding: bool = False,
        **kwargs: Any,
    ) -> dict[str, list[int]]:
        first_ids = list(ids)
        second_ids = list(pair_ids or [])

        if max_length is not None:
            special_tokens = self.num_special_tokens_to_add(pair=bool(second_ids))
            allowed = max_length - special_tokens
            if truncation == "only_second" and second_ids:
                second_ids = second_ids[: max(0, allowed - len(first_ids))]
            elif len(first_ids) + len(second_ids) > allowed:
                overflow = len(first_ids) + len(second_ids) - allowed
                if second_ids:
                    second_ids = second_ids[: max(0, len(second_ids) - overflow)]
                else:
                    first_ids = first_ids[: max(0, len(first_ids) - overflow)]

        cls_token_id = self.cls_token_id
        sep_token_id = self.sep_token_id
        if second_ids:
            input_ids = [cls_token_id] + first_ids + [sep_token_id, sep_token_id]
            input_ids.extend(second_ids + [sep_token_id])
        else:
            input_ids = [cls_token_id] + first_ids + [sep_token_id]
        token_type_ids = [0] * len(input_ids)
        return {
            "input_ids": input_ids,
            "token_type_ids": token_type_ids,
            "attention_mask": [1] * len(input_ids),
        }

    tokenizer.prepare_for_model = MethodType(prepare_for_model, tokenizer)
