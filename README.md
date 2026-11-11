# Nuralis

**An AI research analyst for scientific literature.** Give Nuralis a topic and a year
range; it pulls the relevant papers from arXiv, measures how the field's vocabulary has
shifted over time, indexes the papers for semantic search and writes an analyst-style
briefing with a locally hosted language model.

Everything runs on your own machine. No paper text or query is sent to a third-party
LLM service.

## What you get

| Tab | Contents |
|---|---|
| **Research Intelligence** | Publication volume per year, top keywords, headline metrics for the query |
| **Growth Analysis** | Per-keyword growth rate, rolling averages and base-100 indices; rising / stable / declining classification |
| **Advanced Analytics** | Emerging and declining topics, trend velocity and acceleration, keyword co-occurrence, collaboration statistics, methodology mix |
| **AI Insights** | LLM-written executive summary with paper references, key findings, research gaps, future directions, plus a semantic search box over the retrieved papers |
| **Paper Explorer** | Filterable list of every retrieved paper with authors, categories and arXiv links |

## How it works

```
 query + year range
        │
        ▼
 ┌──────────────────┐   keyword → arXiv category mapping (CS, physics, biology,
 │ Domain detection │   economics, …) so searches are scoped to the right field
 └────────┬─────────┘
          ▼
 ┌──────────────────┐   one arXiv query per year, so every year in
 │ Per-year fetcher │   the range is represented (optionally top-N per year)
 └────────┬─────────┘
          ├──────────────────────────────┬───────────────────────────────┐
          ▼                              ▼                               ▼
 ┌──────────────────┐          ┌──────────────────┐            ┌──────────────────┐
 │  Trend analysis  │          │    Embeddings    │            │     Insights     │
 │ keywords are     │          │ all-MiniLM-L6-v2 │            │ statistics over  │
 │ extracted from   │          │ → ChromaDB       │            │ papers + trends; │
 │ the papers, not  │          │ (cosine search)  │            │ LLM writes the   │
 │ a fixed list     │          │                  │            │ summary          │
 └────────┬─────────┘          └────────┬─────────┘            └────────┬─────────┘
          └──────────────────────────────┴───────────────────────────────┘
                                         ▼
                          JSON response → React dashboard
```

- **Retrieval** — `src/data/fetchers/`. The query is mapped to arXiv categories
  (`domain_detector.py`), then fetched one year at a time, newest submissions first
  (`arxiv_fetcher_optimized.py`). Only arXiv is queried.
- **Trend analysis** — `src/analysis/`. Keywords come from the retrieved titles and
  abstracts (technical terms, n-gram phrases, query terms, ranked by relevance), so the
  analysis works outside machine learning. Growth compares recent against historical
  yearly averages.
- **Semantic search** — `src/ai/embeddings.py`. Titles and abstracts are embedded with
  `all-MiniLM-L6-v2` (384 dimensions) and stored in a persistent ChromaDB collection.
  The collection is replaced on each analysis, so search covers the latest result set.
- **Insights** — `src/ai/advanced_insights.py`. Topic dynamics, gaps, collaboration and
  impact figures are computed directly from the data. The executive summary is generated
  by the LLM from the paper set and cleaned by `src/utils/output_filter.py`.
- **LLM** — `src/ai/llm_manager.py`. Default model is `EleutherAI/gpt-j-6B`, loaded in
  8-bit with bitsandbytes. A local GGUF model can be used instead through llama.cpp.
  With `strict_research_mode` (the default) a failed generation leaves the field empty
  rather than filling it with heuristic text.

## Requirements

| | |
|---|---|
| Python | 3.9 – 3.11 (the pinned PyTorch 2.0 stack has no wheels for 3.12+) |
| Node.js | 18 or newer |
| GPU | Optional. An NVIDIA GPU with ~8 GB free VRAM is needed for the default LLM |
| Disk | ~5 GB for the Python environment; ~12 GB more for the GPT-J weights on first LLM use |
| OS | Linux or macOS (the launcher is a bash script) |

Without a GPU, retrieval, trend analysis, statistics and semantic search all work; the
LLM-written summary is skipped.

## Quick start

```bash
git clone https://github.com/Vc555s/Nuralis.git
cd Nuralis
./start.sh
```

The first run creates `.venv`, installs the Python and npm dependencies, then starts:

- UI — http://localhost:5050
- API — http://localhost:8010 (interactive docs at `/docs`)

Stop with `Ctrl+C`. Later runs skip installation; use `./start.sh --install` after
changing dependencies.

Models are loaded lazily. The first analysis downloads and loads the embedding model
(seconds); the first analysis with *AI insights* enabled also loads the LLM, which
takes several minutes the first time. Both stay in memory afterwards.

To try it without the LLM or a GPU:

```bash
NURALIS_LLM_ENABLED=false ./start.sh
```

### Launcher options

| Option / variable | Effect |
|---|---|
| `--install` | Reinstall Python and npm dependencies |
| `--clean` | Recreate `.venv` and `frontend/node_modules` |
| `--no-frontend` | Start the API only |
| `BACKEND_PORT`, `FRONTEND_PORT` | Ports (defaults 8010 and 5050) |
| `PYTHON_BIN` | Interpreter used to create the virtualenv, e.g. `python3.11` |

### Manual start

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api_server:app --host 0.0.0.0 --port 8010

# second terminal
cd frontend && npm ci && npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8010`. Point it elsewhere with
`VITE_API_PROXY_TARGET` in `frontend/.env.local`.

## Configuration

Settings live in [`config/main_config.yaml`](config/main_config.yaml); every key is
commented there. The ones you are most likely to change:

| Key | Default | Meaning |
|---|---|---|
| `models.llm.name` | `EleutherAI/gpt-j-6B` | Hugging Face causal-LM id, or path to a `.gguf` file |
| `models.llm.enabled` | `true` | Turn the LLM off entirely |
| `models.embeddings.name` | `all-MiniLM-L6-v2` | Sentence-Transformers model |
| `data_sources.arxiv.domain_detection_method` | `keyword` | `keyword`, `llm` or `api` |
| `analysis.trends.max_keywords` | `25` | Keywords kept in the trend output |
| `system.strict_research_mode` | `true` | Never substitute heuristic text for LLM output |
| `system.eager_loading` | `false` | Load models at startup instead of on first use |

Environment variables (see [`.env.example`](.env.example)) override the file:
`NURALIS_LLM_ENABLED`, `NURALIS_LLM_MODEL`, `NURALIS_CONFIG`, and `HF_TOKEN` for gated
models.

**Running the LLM on CPU.** Install `llama-cpp-python`, download a GGUF model and set
`NURALIS_LLM_MODEL=/path/to/model.gguf`. `LLAMA_CPP_THREADS` and `LLAMA_CPP_GPU_LAYERS`
tune it.

## API

### `GET /api/status`

```json
{ "gpu": {"device": "cuda", "total": 25.4, "allocated": 6.9},
  "llmEnabled": true, "llmAvailable": true, "embeddingsAvailable": true }
```

Never triggers a model load; availability flags turn `true` once a model is in memory.

### `POST /api/analyze`

```bash
curl -X POST http://localhost:8010/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"query": "graph neural networks", "startYear": 2020, "endYear": 2024,
       "maxPapers": 200, "enableLLM": true, "enableEmbeddings": true}'
```

| Field | Type | Notes |
|---|---|---|
| `query` | string | Topic to analyse |
| `startYear`, `endYear` | int | Inclusive range, 2000 or later |
| `maxPapers` | int | Total cap, spread evenly across years (default 500) |
| `perYear` | int, optional | Fetch the top N per year instead of an overall cap |
| `enableLLM` | bool | Generate insights; loads the LLM on first use |
| `enableEmbeddings` | bool | Index the papers for semantic search |

Returns `papers`, `trends_data` (`years`, `keywords`, `growth_analysis`, `enrichment`),
`advanced_insights` and `status`.

### `POST /api/semantic-search`

```bash
curl -X POST http://localhost:8010/api/semantic-search \
  -H 'Content-Type: application/json' \
  -d '{"question": "message passing on molecular graphs", "k": 5}'
```

Returns the `k` nearest papers from the last analysis with their metadata and distance.

## Evaluation

The scripts used to measure the system are included:

```bash
pip install -r requirements-eval.txt        # with the API running

make tr   Q="graph neural networks" Y0=2019 Y1=2024   # trend stability and robustness
make se                                               # retrieval quality and latency (gold/judgements.jsonl)
make ll   Q="graph neural networks"                   # summary depth and grounding
make perf                                             # pipeline throughput
python make_all_plots.py                              # figures → results/plots

./scripts/run_all_tests.sh     # end-to-end latency, embedding throughput, retrieval, ROUGE
```

Example figures from an earlier run are in [`results/plots`](results/plots).
Set `EVAL_API_BASE_URL` if the API is not on `http://localhost:8010/api/`.

## Project layout

```
api_server.py            FastAPI app (lazy model loading, three endpoints)
config/main_config.yaml  Runtime configuration
src/
  data/fetchers/         arXiv retrieval and domain detection
  analysis/              Keyword extraction and trend analysis
  ai/                    Embeddings + vector store, LLM manager, insight generation
  evaluation/            Metrics used by the evaluation scripts
  utils/                 Config, logging, GPU helpers, LLM output clean-up
frontend/                React 18 + TypeScript + Vite + Tailwind + shadcn/ui + Recharts
eval/, scripts/, gold/   Evaluation harness and relevance judgements
start.sh                 One-command launcher
```

Runtime data (`chroma_db/`, `logs/`) is created on first use and is git-ignored.

## Limitations

- arXiv is the only source, so coverage follows arXiv's: strong in CS, physics, maths and
  quantitative fields, thin elsewhere. The arXiv API is rate-limited; very large requests
  are slow.
- Analysis uses titles and abstracts, not full text.
- The API has no authentication and allows any origin. Run it on a trusted network.
- GPT-J is a 2021-era model without instruction tuning. Its executive summaries are
  often weak and can simply restate the prompt; the statistical sections do not depend
  on it. Pointing `NURALIS_LLM_MODEL` at a modern instruction-tuned model is the most
  effective upgrade.
- Papers are ranked by submission date within the detected arXiv categories, not by
  relevance, so broad queries return recent papers that merely mention the terms.
- For UI work without a backend, set `VITE_MOCK_MODE=true` in `frontend/.env.local` to
  use built-in sample data. It is never used otherwise.

## License

MIT — see [LICENSE](LICENSE).
