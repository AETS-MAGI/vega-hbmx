# 2026-03-07 codex minimal scope note

## 実施スコープ（今回）
- 実施: 意味の確定、ゲートの表化、最小検証計画の作成。
- 非実施: 広範囲パッチ適用、既存レポートの大幅改稿、`vega_work_log/run_*` の改変。

## D. 同一条件比較の固定テスト手順

### 1) 実行コマンド案（ROCm / Vulkan 同条件）

```bash
cd /home/limonene/ROCm-project/test_loop
source .venv-test/bin/activate

# 共通条件（固定）
export MODEL=qwen3.5:2b
export EPOCHS=1
export NUM_PREDICT=512
export NUM_GPU=0,1,2,-1

# ROCm backend 側（11435）
OLLAMA_HOST=http://127.0.0.1:11435 python vega-loop_qwen_rocm.py

# Vulkan backend 側（11434）
OLLAMA_HOST=http://127.0.0.1:11434 python vega-loop_qwen_rocm.py
```

補足:
- 上記は `model/prompt/num_gpu/epoch/num_predict` を固定し、`OLLAMA_HOST` だけを変える。
- `vega-loop_qwen_rocm.py` は同一フォーマットの `result.json` を生成できるため比較に使う。

### 2) 採取ログ一覧（runディレクトリごと）
- `meta.json`
- `result.json`
- `backend_probe.txt`
- `ollama_journal_since_start.txt`
- `ollama_version.txt`
- `rocminfo_gfx.txt`
- `env.txt`
- `rocm_smi_before.txt`, `rocm_smi_after.txt`
- `ollama_ps_before.txt`, `ollama_ps_after.txt`
- `rocm_smi_epoch_*_before/after.txt`
- `ollama_ps_epoch_*_before/after.txt`
- `responses/epoch_*.txt`

### 3) 判定項目
- `result.json.records[].status`（`ok` / `error`）
- `result.json.records[].error_type`（`http_error`, `connection_error`, `timeout`, `json_decode_error` など）
- `result.json.records[].http_status`
- `result.json.records[].response_error`
- `summary_by_num_gpu` の差分（`0,1,2,-1`）
- `ollama_journal_since_start.txt` の backend 行
  - `load_backend: loaded ROCm backend ...`
  - `load_backend: loaded Vulkan backend ...`
- `SIGSEGV` / `post predict ... EOF` の有無
- crash時スタック（`computeBatch`, `ggml_backend_sched_graph_compute_async`）の有無

### 4) 期待される比較表フォーマット

| run_id | backend_host | backend_from_journal | model | epochs | num_predict | num_gpu | status | error_type | http_status | response_error | sigsegv_in_journal | crash_stack_keyword | elapsed_sec |
|---|---|---|---|---:|---:|---:|---|---|---:|---|---|---|---:|
| run_xxx | 11435 | ROCm | qwen3.5:2b | 1 | 512 | 0 | ok | - | - | - | no | - | 46.7 |
| run_xxx | 11435 | ROCm | qwen3.5:2b | 1 | 512 | 1 | ok | - | - | - | no | - | 48.7 |
| run_xxx | 11434 | Vulkan | qwen3.5:2b | 1 | 512 | 1 | error | http_error | 500 | model runner has unexpectedly stopped... | yes | computeBatch | 2.7 |

## 監査メモ
- `vega_work_log/run_*` は読み取りのみで、削除・改変はしていない。
- 既存レポート本文の大規模改稿は行わず、新規ファイルで補助整理した。
- `num_gpu` はコード根拠で層数意味を確認し、multi-GPU断定を避ける形に統一した。

## 未確定事項
- `num_gpu` 値上昇時に Vulkan で具体的にどのカーネル分岐へ入って crash するか。
- `vega-loop_qwen_rocm.py` の `backend_target` 表記（スクリプト固定値）が、11434実行時の表示と一致しない点。
