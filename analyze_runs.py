"""
analyze_runs.py
===============
vega_work_log/ 以下の全 run を自動収集し、以下を出力する。

  1. 全レコードフラット表（run_id, backend, version, num_gpu, status, elapsed, eval_count）
  2. backend × num_gpu 集計ピボット（ok/total）
  3. Vulkan クラッシュ timing 統計（num_gpu≥1 の elapsed_sec の一貫性）
  4. Vulkan num_gpu=0 連続安定性
  5. markdown 形式での summary（発表前追い込み実験結果.md に貼りやすい形）

Usage:
  python analyze_runs.py              # 標準出力
  python analyze_runs.py --csv        # records.csv も出力
  python analyze_runs.py --md         # summary.md を出力（発表前追い込み実験結果.md 用）
"""

import json
import sys
import statistics
from pathlib import Path
from datetime import datetime

# ── 設定 ──────────────────────────────────────────────────────────────────
LOG_ROOT = Path(__file__).resolve().parent / "vega_work_log"
EXPORT_CSV = "--csv" in sys.argv
EXPORT_MD  = "--md"  in sys.argv

# ── ヘルパー ───────────────────────────────────────────────────────────────
def detect_backend(run_dir: Path, result: dict, meta: dict) -> str:
    """backend 文字列を推定する。"""
    # result.json の backend_target フィールド
    bt = result.get("backend_target", "")
    if bt:
        # ollama_host で ROCm/Vulkan を区別
        host = result.get("ollama_host", meta.get("environment", {}).get("OLLAMA_HOST", ""))
        if "11435" in str(host):
            return "ROCm"
        if "11434" in str(host):
            return "Vulkan"
        return bt

    # ollama_host から判断
    host = result.get("ollama_host") or meta.get("ollama_host") or meta.get("environment", {}).get("OLLAMA_HOST", "")
    if "11435" in str(host):
        return "ROCm"
    if "11434" in str(host):
        return "Vulkan"

    # backend_probe.txt から推定
    probe = run_dir / "backend_probe.txt"
    if probe.exists():
        text = probe.read_text(errors="ignore")
        if "libggml-hip" in text or "ROCm" in text:
            return "ROCm"
        if "libggml-vulkan" in text or "Vulkan" in text:
            return "Vulkan"

    return "unknown"


def read_ollama_version(run_dir: Path) -> str:
    vf = run_dir / "ollama_version.txt"
    if vf.exists():
        line = vf.read_text().strip()
        # "ollama version is 0.17.4" など
        parts = line.split()
        return parts[-1] if parts else "?"
    return "?"


def read_hsa_override(meta: dict) -> str:
    env = meta.get("environment", {})
    val = env.get("HSA_OVERRIDE_GFX_VERSION")
    return val if val else "none"


def load_run(run_dir: Path) -> list[dict]:
    """1 run_dir から レコードリストを返す。"""
    result_file = run_dir / "result.json"
    meta_file   = run_dir / "meta.json"

    if not result_file.exists():
        return []

    result = json.loads(result_file.read_text())
    meta   = json.loads(meta_file.read_text()) if meta_file.exists() else {}

    run_id  = result.get("run_id", run_dir.name)
    backend = detect_backend(run_dir, result, meta)
    version = read_ollama_version(run_dir)
    model   = result.get("model", "?")
    hsa     = read_hsa_override(meta)
    num_predict = result.get("num_predict", "?")

    rows = []
    for rec in result.get("records", []):
        rows.append({
            "run_id":      run_id,
            "date":        run_id[4:12],          # run_YYYYMMDD_...
            "backend":     backend,
            "version":     version,
            "hsa_override": hsa,
            "model":       model,
            "num_predict": num_predict,
            "num_gpu":     rec.get("num_gpu", result.get("num_gpu", "?")),
            "status":      rec.get("status", "?"),
            "elapsed_sec": rec.get("elapsed_sec"),
            "eval_count":  rec.get("eval_count"),
            "error_type":  rec.get("error_type", ""),
        })
    return rows


# ── データ収集 ────────────────────────────────────────────────────────────
all_rows: list[dict] = []
for run_dir in sorted(LOG_ROOT.iterdir()):
    if run_dir.is_dir() and run_dir.name.startswith("run_"):
        all_rows.extend(load_run(run_dir))

if not all_rows:
    print("❌ レコードが見つかりませんでした。LOG_ROOT を確認してください:", LOG_ROOT)
    sys.exit(1)

# ── 1. フラット表 ──────────────────────────────────────────────────────────
def fmt_status(s: str) -> str:
    return "✅ ok" if s == "ok" else f"❌ {s}"

def fmt_elapsed(v) -> str:
    return f"{v:.2f}s" if isinstance(v, float) else "—"

def fmt_eval(v) -> str:
    return str(v) if v is not None else "—"

COL = {
    "run_id":      24,
    "date":         8,
    "backend":      8,
    "version":      7,
    "hsa_override": 12,
    "model":       12,
    "num_gpu":      8,
    "status":      10,
    "elapsed_sec": 10,
    "eval_count":   8,
}

def hdr(d): return str(d).ljust(COL.get(d, 12))
def cel(d, v): return str(v).ljust(COL.get(d, 12))

print("=" * 100)
print("1. 全レコード フラット表")
print("=" * 100)
print(" ".join(hdr(k) for k in COL))
print("-" * 100)
for r in all_rows:
    print(
        cel("run_id",      r["run_id"]) +
        cel("date",        r["date"]) +
        cel("backend",     r["backend"]) +
        cel("version",     r["version"]) +
        cel("hsa_override",r["hsa_override"]) +
        cel("model",       r["model"][:12]) +
        cel("num_gpu",     r["num_gpu"]) +
        cel("status",      r["status"]) +
        cel("elapsed_sec", fmt_elapsed(r["elapsed_sec"])) +
        cel("eval_count",  fmt_eval(r["eval_count"]))
    )

# ── 2. backend × num_gpu ピボット ──────────────────────────────────────────
print()
print("=" * 60)
print("2. backend × num_gpu 集計ピボット（qwen3.5:2b のみ）")
print("=" * 60)

from collections import defaultdict
pivot: dict[tuple, dict] = defaultdict(lambda: {"ok": 0, "error": 0, "elapsed": [], "eval": []})

for r in all_rows:
    if r["model"] != "qwen3.5:2b":
        continue
    key = (r["backend"], r["num_gpu"])
    pivot[key][r["status"]] = pivot[key].get(r["status"], 0) + 1
    if r["elapsed_sec"] is not None:
        pivot[key]["elapsed"].append(r["elapsed_sec"])
    if r["eval_count"] is not None:
        pivot[key]["eval"].append(r["eval_count"])

backends  = sorted({k[0] for k in pivot})
num_gpus  = sorted({k[1] for k in pivot}, key=lambda x: (x == "?" or x is None, x if isinstance(x, int) else 0))

print(f"{'backend':<10} {'num_gpu':>8} {'ok':>5} {'error':>6} {'total':>6}  {'ok%':>6}  {'elapsed_mean':>13}  {'elapsed_std':>11}")
print("-" * 80)
for b in backends:
    for ng in num_gpus:
        key = (b, ng)
        if key not in pivot:
            continue
        d = pivot[key]
        ok    = d.get("ok", 0)
        err   = d.get("error", 0)
        total = ok + err
        pct   = f"{ok/total*100:.0f}%" if total else "—"
        elaps = d["elapsed"]
        emean = f"{statistics.mean(elaps):.2f}s" if elaps else "—"
        estd  = f"±{statistics.stdev(elaps):.2f}s" if len(elaps) >= 2 else "—"
        print(f"{b:<10} {str(ng):>8} {ok:>5} {err:>6} {total:>6}  {pct:>6}  {emean:>13}  {estd:>11}")
    print()

# ── 3. Vulkan クラッシュ timing 統計 ──────────────────────────────────────
print("=" * 60)
print("3. Vulkan クラッシュ timing（num_gpu≥1 の elapsed_sec）")
print("=" * 60)

crash_by_ng: dict = defaultdict(list)
for r in all_rows:
    if r["backend"] == "Vulkan" and r["status"] == "error" and isinstance(r["num_gpu"], int) and r["num_gpu"] != 0:
        if r["elapsed_sec"] is not None:
            crash_by_ng[r["num_gpu"]].append((r["run_id"], r["elapsed_sec"]))

print(f"{'num_gpu':>8}  {'n':>3}  {'mean':>8}  {'std':>8}  {'min':>8}  {'max':>8}  values")
print("-" * 75)
for ng, entries in sorted(crash_by_ng.items()):
    vals = [e[1] for e in entries]
    mean = statistics.mean(vals)
    std  = statistics.stdev(vals) if len(vals) >= 2 else 0.0
    print(f"{ng:>8}  {len(vals):>3}  {mean:>7.3f}s  {std:>7.3f}s  {min(vals):>7.3f}s  {max(vals):>7.3f}s  {[round(v,3) for v in vals]}")

# ── 4. Vulkan num_gpu=0 連続安定性 ────────────────────────────────────────
print()
print("=" * 60)
print("4. Vulkan num_gpu=0 連続安定性")
print("=" * 60)

vk0 = [(r["run_id"], r["elapsed_sec"], r["eval_count"])
       for r in all_rows
       if r["backend"] == "Vulkan" and r["num_gpu"] == 0 and r["status"] == "ok"]

print(f"  ok件数: {len(vk0)}")
elapsed_vals = [e for _, e, _ in vk0 if e is not None]
if elapsed_vals:
    print(f"  elapsed mean: {statistics.mean(elapsed_vals):.2f}s  std: {statistics.stdev(elapsed_vals) if len(elapsed_vals)>=2 else 0:.2f}s")
    print(f"  elapsed range: {min(elapsed_vals):.2f}s ~ {max(elapsed_vals):.2f}s")
print(f"  全 eval_count=512: {all(e==512 for _,_,e in vk0 if e is not None)}")

# ── 5. tinyllama 参考データ（存在する場合）──────────────────────────────
tiny = [r for r in all_rows if r["model"] == "tinyllama:latest"]
if tiny:
    print()
    print("=" * 60)
    print("5. tinyllama 参考データ")
    print("=" * 60)
    for r in tiny[:10]:
        print(f"  {r['run_id']}  {r['backend']:<8}  num_gpu={r['num_gpu']}  {r['status']}  {fmt_elapsed(r['elapsed_sec'])}")
    if len(tiny) > 10:
        print(f"  ... （全 {len(tiny)} 件）")

# ── 6. Markdown サマリ ────────────────────────────────────────────────────
md_lines = []
md_lines.append("## 分析サマリ（analyze_runs.py 出力）\n")
md_lines.append(f"**生成日時:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
md_lines.append(f"**総レコード数:** {len(all_rows)}\n")
md_lines.append(f"**run数:** {len(set(r['run_id'] for r in all_rows))}\n")
md_lines.append("")

md_lines.append("### backend × num_gpu 集計（qwen3.5:2b）\n")
md_lines.append("| backend | num_gpu | ok | error | total | ok% | elapsed_mean | elapsed_std |")
md_lines.append("|---|---|---|---|---|---|---|---|")
for b in backends:
    for ng in num_gpus:
        key = (b, ng)
        if key not in pivot:
            continue
        d = pivot[key]
        ok    = d.get("ok", 0)
        err   = d.get("error", 0)
        total = ok + err
        pct   = f"{ok/total*100:.0f}%" if total else "—"
        elaps = d["elapsed"]
        emean = f"{statistics.mean(elaps):.2f}s" if elaps else "—"
        estd  = f"±{statistics.stdev(elaps):.2f}s" if len(elaps) >= 2 else "—"
        md_lines.append(f"| {b} | {ng} | {ok} | {err} | {total} | {pct} | {emean} | {estd} |")

md_lines.append("")
md_lines.append("### Vulkan クラッシュ timing（num_gpu≥1）\n")
md_lines.append("| num_gpu | n | mean | std | values |")
md_lines.append("|---|---|---|---|---|")
for ng, entries in sorted(crash_by_ng.items()):
    vals = [e[1] for e in entries]
    mean = statistics.mean(vals)
    std  = statistics.stdev(vals) if len(vals) >= 2 else 0.0
    md_lines.append(f"| {ng} | {len(vals)} | {mean:.3f}s | {std:.3f}s | {[round(v,3) for v in vals]} |")

md_lines.append("")
md_lines.append(f"### Vulkan num_gpu=0 安定性\n")
md_lines.append(f"- ok 件数: {len(vk0)}")
if elapsed_vals:
    md_lines.append(f"- elapsed mean: {statistics.mean(elapsed_vals):.2f}s (std: {statistics.stdev(elapsed_vals) if len(elapsed_vals)>=2 else 0:.2f}s)")
md_lines.append(f"- 全 eval_count=512: {all(e==512 for _,_,e in vk0 if e is not None)}")

md_summary = "\n".join(md_lines)

print()
print("=" * 60)
print("6. Markdown サマリ（--md で summary.md に保存）")
print("=" * 60)
print(md_summary)

# ── オプション出力 ────────────────────────────────────────────────────────
if EXPORT_CSV:
    import csv
    out_csv = Path(__file__).parent / "analysis_records.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n✅ CSV 保存: {out_csv}")

if EXPORT_MD:
    out_md = Path(__file__).parent / "analysis_summary.md"
    out_md.write_text(md_summary, encoding="utf-8")
    print(f"\n✅ Markdown 保存: {out_md}")
