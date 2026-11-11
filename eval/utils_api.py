import os
import time
import json
import typing as t
from dataclasses import dataclass
from urllib.parse import urljoin

import requests


DEFAULT_API_BASE = os.environ.get("EVAL_API_BASE_URL", "http://localhost:8010/api/")


@dataclass
class AnalyzeParams:
    query: str
    year_start: int
    year_end: int
    max_papers: int = 500
    use_llm: bool = False
    use_embeddings: bool = False


class ApiError(Exception):
    pass


def _post_json(path: str, payload: dict, base: str = DEFAULT_API_BASE, timeout: float = 120.0,
               retries: int = 3, backoff: float = 0.7) -> dict:
    url = urljoin(base if base.endswith('/') else base + '/', path.lstrip('/'))
    last_exc: t.Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code >= 400:
                raise ApiError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt == retries - 1:
                break
            time.sleep((attempt + 1) * backoff)
    raise ApiError(f"POST {url} failed after {retries} attempts: {last_exc}")


def _get_json(path: str, base: str = DEFAULT_API_BASE, timeout: float = 30.0) -> dict:
    url = urljoin(base if base.endswith('/') else base + '/', path.lstrip('/'))
    resp = requests.get(url, timeout=timeout)
    if resp.status_code >= 400:
        raise ApiError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def analyze(
    query: str,
    year_start: int,
    year_end: int,
    *,
    use_llm: bool = False,
    use_embeddings: bool = False,
    max_papers: int = 500,
    api_base: str = DEFAULT_API_BASE,
) -> dict:
    payload = {
        # Map to backend's expected keys
        "query": query,
        "startYear": int(year_start),
        "endYear": int(year_end),
        "maxPapers": int(max_papers),
        "enableLLM": bool(use_llm),
        "enableEmbeddings": bool(use_embeddings),
    }
    return _post_json("/analyze", payload, base=api_base)


def semantic_search(query: str, k: int = 10, *, api_base: str = DEFAULT_API_BASE) -> t.List[dict]:
    payload = {"question": query, "k": int(k)}
    data = _post_json("/semantic-search", payload, base=api_base)
    if not isinstance(data, list):
        raise ApiError("semantic-search returned non-list payload")
    return data


def get_status(*, api_base: str = DEFAULT_API_BASE) -> dict:
    return _get_json("/status", base=api_base)


def ensure_results_dir(path: str = "results") -> str:
    os.makedirs(path, exist_ok=True)
    return path


def dump_json(obj: t.Any, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


