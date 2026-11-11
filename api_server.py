"""
Nuralis API server.

Endpoints
---------
GET  /api/status           model availability
POST /api/analyze          fetch papers -> trend analysis -> embeddings -> LLM insights
POST /api/semantic-search  vector search over the papers indexed by the last analyses

The server starts instantly: the embedding model and the LLM are loaded on the first
request that needs them and are then kept in memory for the lifetime of the process.

Environment overrides (see .env.example)
----------------------------------------
NURALIS_CONFIG        path to the YAML config (default: config/main_config.yaml)
NURALIS_LLM_ENABLED   "false" to run without the local LLM
NURALIS_LLM_MODEL     Hugging Face model id or path to a .gguf file
"""
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent

try:  # optional: picks up HF_TOKEN etc. from a local .env
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

from src.utils.config_loader import load_config
from src.utils.logging_utils import logger

# Read by the arXiv fetcher for LLM-based domain detection (sys.modules["api_server"].llm_manager).
llm_manager = None


class AnalyzeRequest(BaseModel):
    query: str
    startYear: int
    endYear: int
    maxPapers: int = 500
    perYear: Optional[int] = None  # top-N papers per year instead of an overall cap
    enableLLM: bool = True
    enableEmbeddings: bool = True


class SemanticSearchRequest(BaseModel):
    question: str
    k: Optional[int] = 3


def _env_flag(name: str) -> Optional[bool]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return value.strip().lower() in ("1", "true", "yes", "on")


def _load_app_config() -> Dict[str, Any]:
    config = load_config(os.getenv("NURALIS_CONFIG", str(ROOT_DIR / "config" / "main_config.yaml")))
    llm_cfg = config.setdefault("models", {}).setdefault("llm", {})
    enabled = _env_flag("NURALIS_LLM_ENABLED")
    if enabled is not None:
        llm_cfg["enabled"] = enabled
    if os.getenv("NURALIS_LLM_MODEL"):
        llm_cfg["name"] = os.environ["NURALIS_LLM_MODEL"]
    return config


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nuralis API",
        description="Research intelligence: literature retrieval, trend analysis and LLM insights",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    config = _load_app_config()
    llm_cfg = config["models"]["llm"]
    llm_enabled = bool(llm_cfg.get("enabled", True))
    system_cfg = config.get("system", {})

    # Heavy components, created lazily. One lock per component so concurrent
    # requests never load the same model twice.
    state: Dict[str, Any] = {"llm": None, "llm_failed": False, "embeddings": None, "insights": None}
    llm_lock = threading.Lock()
    embeddings_lock = threading.Lock()
    insights_lock = threading.Lock()

    def _llm_can_run_here() -> bool:
        """Hugging Face models are loaded in 8-bit (bitsandbytes), which needs CUDA.
        GGUF models run through llama.cpp and work on CPU."""
        name = str(llm_cfg.get("name", ""))
        if name.lower().endswith(".gguf"):
            return True
        import torch

        return torch.cuda.is_available()

    def get_llm():
        if not llm_enabled or state["llm_failed"]:
            return None
        if state["llm"] is None:
            with llm_lock:
                if state["llm"] is None and not state["llm_failed"]:
                    try:
                        if not _llm_can_run_here():
                            raise RuntimeError(
                                "no CUDA device found; 8-bit loading needs a GPU "
                                "(set NURALIS_LLM_MODEL to a .gguf file to run on CPU)"
                            )
                        from src.ai.llm_manager import LLMManager

                        logger.info(f"⏳ Loading LLM {llm_cfg.get('name')} (first use only)...")
                        start = time.time()
                        state["llm"] = LLMManager(config)
                        sys.modules[__name__].llm_manager = state["llm"]
                        logger.info(f"✅ LLM loaded in {time.time() - start:.1f}s")
                    except Exception as exc:
                        # Do not retry on every request: a failed load costs minutes.
                        state["llm_failed"] = True
                        logger.warning(f"LLM unavailable, continuing without it: {exc}")
        return state["llm"]

    def get_embeddings():
        if state["embeddings"] is None:
            with embeddings_lock:
                if state["embeddings"] is None:
                    try:
                        from src.ai.embeddings import EmbeddingManager

                        logger.info("⏳ Loading embedding model (first use only)...")
                        start = time.time()
                        state["embeddings"] = EmbeddingManager(config)
                        logger.info(f"✅ Embeddings ready in {time.time() - start:.1f}s")
                    except Exception as exc:
                        logger.warning(f"Embeddings unavailable: {exc}")
        return state["embeddings"]

    def get_insights(llm):
        with insights_lock:
            current = state["insights"]
            if current is None or getattr(current, "llm_manager", None) is not llm:
                try:
                    from src.ai.advanced_insights import AdvancedInsightsGenerator

                    state["insights"] = AdvancedInsightsGenerator(config, llm)
                except Exception as exc:
                    logger.warning(f"Insights generator unavailable: {exc}")
                    state["insights"] = None
            return state["insights"]

    def _available(component) -> bool:
        return bool(component and hasattr(component, "is_available") and component.is_available())

    def _gpu_info() -> Dict[str, Any]:
        """Report the device without importing torch just for a status call."""
        torch = sys.modules.get("torch")
        if torch is None:
            return {"device": "unknown", "total": None, "allocated": None}
        if not torch.cuda.is_available():
            return {"device": "cpu", "total": None, "allocated": None}
        return {
            "device": "cuda",
            "total": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2),
            "allocated": round(torch.cuda.memory_allocated(0) / 1e9, 2),
        }

    # Optional warm-up, controlled from config/main_config.yaml -> system
    if system_cfg.get("eager_loading", False):
        logger.info("Eager loading: models load before the server accepts requests")
        get_embeddings()
        get_llm()
    elif system_cfg.get("background_preload_llm", False) and llm_enabled:
        threading.Thread(target=get_llm, daemon=True).start()
    else:
        logger.info("Lazy mode: models load on the first request that needs them")

    @app.get("/api/status")
    def status() -> Dict[str, Any]:
        """Cheap status check: never triggers a model load."""
        return {
            "gpu": _gpu_info(),
            "llmEnabled": llm_enabled,
            "llmAvailable": llm_enabled and _available(state["llm"]),
            "embeddingsAvailable": _available(state["embeddings"]),
        }

    @app.post("/api/analyze")
    def analyze(body: AnalyzeRequest) -> Dict[str, Any]:
        if not body.query.strip() or body.startYear > body.endYear:
            raise HTTPException(status_code=400, detail="Invalid query or year range")

        start_time = time.time()
        logger.info(f"📊 Analysis request: {body.query} ({body.startYear}-{body.endYear})")

        # Only load what this request asked for.
        llm = get_llm() if body.enableLLM else None
        embeddings = get_embeddings() if body.enableEmbeddings else None

        config["data_sources"]["arxiv"]["max_results"] = int(body.maxPapers)

        # 1. Retrieval
        fetch_start = time.time()
        try:
            from src.data.fetchers.arxiv_fetcher_optimized import OptimizedArxivFetcher

            fetcher = OptimizedArxivFetcher(config)
        except Exception as exc:
            logger.warning(f"Parallel fetcher unavailable, using the sequential one: {exc}")
            from src.data.fetchers.arxiv_fetcher import ArxivFetcher

            fetcher = ArxivFetcher(config)

        if body.perYear and body.perYear > 0:
            papers = fetcher.search_with_date_distribution(
                body.query, body.startYear, body.endYear, per_year=body.perYear
            ) or []
        else:
            papers = fetcher.search_with_date_distribution(body.query, body.startYear, body.endYear) or []
        logger.info(f"✅ Fetched {len(papers)} papers in {time.time() - fetch_start:.1f}s")

        # 2. Trend analysis
        trends_start = time.time()
        try:
            from src.analysis.trend_analyzer_optimized import OptimizedTrendAnalyzer

            analyzer = OptimizedTrendAnalyzer(config, query=body.query)
        except Exception as exc:
            logger.warning(f"Parallel trend analyzer unavailable, using the basic one: {exc}")
            from src.analysis.trend_analyzer import TrendAnalyzer

            analyzer = TrendAnalyzer(config)
        trends_data: Dict[str, Any] = analyzer.analyze_trends(papers) or {"years": [], "keywords": {}}
        logger.info(f"✅ Trends analysed in {time.time() - trends_start:.1f}s")

        # 3. Embeddings -> vector store (enables /api/semantic-search)
        if _available(embeddings):
            try:
                emb_start = time.time()
                embeddings.add_papers_to_store(papers)
                logger.info(f"✅ Papers indexed in {time.time() - emb_start:.1f}s")
            except Exception as exc:
                logger.warning(f"Indexing failed: {exc}")

        # 4. Insights (statistical analysis; executive summary when the LLM is loaded)
        advanced_insights: Optional[Dict[str, Any]] = None
        if body.enableLLM:
            generator = get_insights(llm)
            if generator:
                try:
                    insights_start = time.time()
                    advanced_insights = generator.generate_comprehensive_insights(papers, trends_data, body.query)
                    logger.info(f"✅ Insights generated in {time.time() - insights_start:.1f}s")
                except Exception as exc:
                    logger.warning(f"Insight generation failed: {exc}")

        logger.info(f"⏱️  Total analysis: {time.time() - start_time:.1f}s")

        return {
            "papers": papers,
            "trends_data": trends_data,
            "status": status(),
            "advanced_insights": advanced_insights,
            # Reserved for the frontend; not computed by this server.
            "citation_network": None,
            "impact_scores": None,
            "trend_predictions": None,
        }

    @app.post("/api/semantic-search")
    def semantic_search(body: SemanticSearchRequest) -> List[Dict[str, Any]]:
        embeddings = get_embeddings()
        if not _available(embeddings):
            raise HTTPException(status_code=503, detail="Embeddings not available")
        try:
            start = time.time()
            results = embeddings.semantic_search(body.question, k=body.k or 3) or []
            logger.info(f"✅ Semantic search in {time.time() - start:.2f}s")
            return results
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Semantic search failed: {exc}")

    return app


app = create_app()
