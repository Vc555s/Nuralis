RESULTS=results
PY=python3

.PHONY: results tr se ll perf

results:
	mkdir -p $(RESULTS)

# Default query/year span can be overridden: make tr Q="graph neural networks" Y0=2019 Y1=2024
Q?=transformer attention mechanisms
Y0?=2018
Y1?=2024

tr: results
	$(PY) -m eval.eval_tr_temporal_stability --query "$(Q)" --year-start $(Y0) --year-end $(Y1)
	$(PY) -m eval.eval_tr_growth_robustness --query "$(Q)" --year-start $(Y0) --year-end $(Y1)
	@echo "[tr] done for $(Q) $(Y0)-$(Y1)"

se: results
	$(PY) -m eval.eval_se_quality --judgments gold/judgements.jsonl
	$(PY) -m eval.bench_se_latency --judgments gold/judgements.jsonl
	@echo "[se] done"

ll: results
	$(PY) -m eval.eval_ll_depth_helper --query "$(Q)" --year-start $(Y0) --year-end $(Y1)
	$(PY) -m eval.eval_ll_grounding --query "$(Q)" --year-start $(Y0) --year-end $(Y1)
	@echo "[ll] done for $(Q) $(Y0)-$(Y1)"

perf: results
	$(PY) -m eval.bench_pipeline_perf --query "$(Q)" --year-start $(Y0) --year-end $(Y1)
	@echo "[perf] done"


