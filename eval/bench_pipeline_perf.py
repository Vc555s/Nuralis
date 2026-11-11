import argparse
import csv
import os
import threading
import time
from typing import Dict, Optional

import psutil

try:
    import pynvml  # type: ignore
    _NVML_AVAILABLE = True
except Exception:  # noqa: BLE001
    _NVML_AVAILABLE = False

from .utils_api import analyze, ensure_results_dir


class Sampler(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True)
        self._running = threading.Event()
        self._running.set()
        self.cpu: list[float] = []
        self.ram_gb: list[float] = []
        self.vram_gb: list[float] = []

    def run(self) -> None:  # noqa: D401
        process = psutil.Process(os.getpid())
        if _NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except Exception:  # noqa: BLE001
                handle = None
        else:
            handle = None

        while self._running.is_set():
            try:
                self.cpu.append(psutil.cpu_percent(interval=None))
                mem = psutil.virtual_memory().used / (1024 ** 3)
                self.ram_gb.append(mem)
                if handle is not None:
                    try:
                        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        self.vram_gb.append(info.used / (1024 ** 3))
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)

    def stop(self) -> None:
        self._running.clear()

    def summary(self) -> Dict[str, Optional[float]]:
        return {
            "cpu_mean": sum(self.cpu) / len(self.cpu) if self.cpu else None,
            "ram_peak_gb": max(self.ram_gb) if self.ram_gb else None,
            "vram_peak_gb": max(self.vram_gb) if self.vram_gb else None,
        }


def run_once(config_name: str, *, query: str, y0: int, y1: int, use_llm: bool, use_emb: bool, api_base: str) -> Dict[str, Optional[float]]:
    sampler = Sampler()
    sampler.start()
    t0 = time.perf_counter()
    _ = analyze(query, y0, y1, use_llm=use_llm, use_embeddings=use_emb, api_base=api_base)
    t1 = time.perf_counter()
    time.sleep(0.5)
    sampler.stop()
    sampler.join(timeout=2.0)
    s = sampler.summary()
    s.update({
        "config": config_name,
        "wall_time_s": t1 - t0,
    })
    return s


def main() -> None:
    parser = argparse.ArgumentParser(description="PF-02 End-to-End Performance (LLM ON/OFF + resources)")
    parser.add_argument("--query", default="transformer attention mechanisms")
    parser.add_argument("--year-start", type=int, default=2018)
    parser.add_argument("--year-end", type=int, default=2024)
    parser.add_argument("--api-base", default=os.environ.get("EVAL_API_BASE_URL", "http://localhost:8010/api/"))
    args = parser.parse_args()

    results_dir = ensure_results_dir("results")
    csv_path = os.path.join(results_dir, "pipeline_perf.csv")

    rows: list[Dict[str, Optional[float]]] = []
    # (A) LLM OFF, Embeddings OFF
    rows.append(run_once("A_off_off_run1", query=args.query, y0=args.year_start, y1=args.year_end, use_llm=False, use_emb=False, api_base=args.api_base))
    time.sleep(5)
    rows.append(run_once("A_off_off_run2", query=args.query, y0=args.year_start, y1=args.year_end, use_llm=False, use_emb=False, api_base=args.api_base))

    # (B) LLM ON, Embeddings ON
    time.sleep(5)
    rows.append(run_once("B_on_on_run1", query=args.query, y0=args.year_start, y1=args.year_end, use_llm=True, use_emb=True, api_base=args.api_base))
    time.sleep(5)
    rows.append(run_once("B_on_on_run2", query=args.query, y0=args.year_start, y1=args.year_end, use_llm=True, use_emb=True, api_base=args.api_base))

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["config", "wall_time_s", "cpu_mean", "ram_peak_gb", "vram_peak_gb"]) 
        writer.writeheader()
        writer.writerows(rows)

    def p(vals: list[float], q: float) -> float:
        s = sorted(vals)
        idx = int(round(q * (len(s) - 1)))
        return s[idx]

    for cfg in ("A_off_off", "B_on_on"):
        cfg_rows = [r for r in rows if r["config"] and str(r["config"]).startswith(cfg)]
        times = [float(r["wall_time_s"]) for r in cfg_rows]
        print(f"{cfg}: p50={p(times,0.5):.2f}s p95={p(times,0.95):.2f}s")


if __name__ == "__main__":
    main()


