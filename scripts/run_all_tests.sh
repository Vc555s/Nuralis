#!/bin/bash
# Master test runner for Nuralis Standardized Testing Protocol
# Runs all 4 tests in sequence

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧠 NURALIS — STANDARDIZED TESTING PROTOCOL${NC}"
echo "=========================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if API server is running
echo -e "${BLUE}Checking API server status...${NC}"
if curl -s http://localhost:8010/api/status > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API server is running${NC}"
else
    echo -e "${RED}❌ API server is not running${NC}"
    echo "Please start the API server first:"
    echo "  cd $PROJECT_DIR && ./start.sh --no-frontend"
    exit 1
fi

# Create test results directories
mkdir -p test_results/data/{e2e,embeddings,relevance,llm_eval}
mkdir -p test_results/logs/gpu

# TEST 1: End-to-End Latency
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}TEST 1: End-to-End Latency Evaluation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
python scripts/test_1_e2e_latency.py \
    --api-url http://localhost:8010 \
    --query "transformer attention mechanisms" \
    --start-year 2020 \
    --end-year 2024 \
    --max-papers 500 \
    --num-runs 5 \
    --output test_results/data/e2e/e2e_summary.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ TEST 1 completed${NC}"
else
    echo -e "${RED}❌ TEST 1 failed${NC}"
fi

# TEST 2: Embedding Throughput (requires test data)
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}TEST 2: Embedding Throughput Analysis${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if test data exists
if [ ! -f "test_results/data/embeddings/abstracts_2k.json" ]; then
    echo -e "${YELLOW}⚠️  Test data not found. Generating...${NC}"
    python scripts/generate_test_data.py \
        --query "machine learning" \
        --max-results 2000 \
        --output test_results/data/embeddings/abstracts_2k.json
fi

# Start GPU monitoring in background (if nvidia-smi is available)
if command -v nvidia-smi &> /dev/null; then
    echo -e "${BLUE}Starting GPU monitoring...${NC}"
    nvidia-smi dmon -s pucmt -o DT -f test_results/logs/gpu/gpu_log.csv &
    GPU_MONITOR_PID=$!
    trap "kill $GPU_MONITOR_PID 2>/dev/null" EXIT
fi

python scripts/test_2_embedding_throughput.py \
    --input test_results/data/embeddings/abstracts_2k.json \
    --batches 8 16 32 64 \
    --num-runs 3 \
    --output test_results/data/embeddings/emb_throughput.json

# Stop GPU monitoring
if [ ! -z "$GPU_MONITOR_PID" ]; then
    kill $GPU_MONITOR_PID 2>/dev/null || true
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ TEST 2 completed${NC}"
else
    echo -e "${RED}❌ TEST 2 failed${NC}"
fi

# TEST 3: Semantic Retrieval (requires ground truth)
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}TEST 3: Semantic Retrieval Evaluation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ ! -f "test_results/data/relevance/relevance.json" ]; then
    echo -e "${YELLOW}⚠️  Ground truth file not found${NC}"
    echo "Using template: test_results/data/relevance/relevance_template.json"
    echo "Please create test_results/data/relevance/relevance.json with your ground truth data"
    
    if [ -f "test_results/data/relevance/relevance_template.json" ]; then
        echo -e "${YELLOW}Skipping TEST 3 (no ground truth data)${NC}"
    else
        echo -e "${RED}❌ Template file not found${NC}"
    fi
else
    python scripts/test_3_semantic_retrieval.py \
        --input test_results/data/relevance/relevance.json \
        --top-k 10 \
        --output test_results/data/relevance/relevance_eval.json
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ TEST 3 completed${NC}"
    else
        echo -e "${RED}❌ TEST 3 failed${NC}"
    fi
fi

# TEST 4: LLM Output Quality (requires reference and generated summaries)
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}TEST 4: LLM Output Quality Evaluation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ ! -f "test_results/data/llm_eval/references.txt" ] || [ ! -f "test_results/data/llm_eval/generated.txt" ]; then
    echo -e "${YELLOW}⚠️  Reference or generated summaries not found${NC}"
    echo "Please create:"
    echo "  - test_results/data/llm_eval/references.txt (reference summaries, one per line)"
    echo "  - test_results/data/llm_eval/generated.txt (generated summaries, one per line)"
    echo -e "${YELLOW}Skipping TEST 4${NC}"
else
    python scripts/test_4_llm_quality.py \
        --refs test_results/data/llm_eval/references.txt \
        --hyps test_results/data/llm_eval/generated.txt \
        --output test_results/data/llm_eval/rouge_results.json \
        --create-template \
        --human-template test_results/data/llm_eval/human_ratings_template.csv
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ TEST 4 completed${NC}"
    else
        echo -e "${RED}❌ TEST 4 failed${NC}"
    fi
fi

# Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Results saved in: test_results/data/"
echo ""
echo "Next steps:"
echo "1. Review test results in test_results/data/"
echo "2. Create figures and tables for Chapter 4 report"
echo "3. For TEST 3: Update ground truth file with actual paper IDs"
echo "4. For TEST 4: Collect human ratings using the generated template"

