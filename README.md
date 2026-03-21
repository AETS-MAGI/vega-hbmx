# Vega / gfx900 実験ワークスペース

更新日: 2026-03-22 (JST)

## 0. このリポジトリの役割

このリポジトリは、Vega / `gfx900` 系の実験を実際に回し、ログとスクリプトを積み上げるための作業用ワークスペースです。
`vega_investigations` が「結果と解釈を整理する正本」なのに対し、こちらは「比較実験・検証コード・生ログを集める実行環境」を担います。

### ここに置くもの

- 比較実験用スクリプト
- loop / benchmark / probe の実行コード
- 生ログ、run ディレクトリ、lab note、notebook
- 試行錯誤の途中経過や一時的な検証ファイル
- 後で調査レポートへ昇格する前の raw な観測結果

### 主に置かないもの

- 最終結論として固定した文章
- 公開ページ向けの完成文
- GPU ごとの整理が済んだ canonical な結果まとめ

## 1. この README で扱う範囲

以下は、このワークスペースで何を回し、何が観測されたかを素早く確認するための実験サマリです。
最終的な整理や GPU ごとの位置づけは、必要に応じて `vega_investigations` 側へ移して扱います。

## 2. 3行結論
- 同一条件比較では、**ROCm/HIP backend は qwen3.5:2b を通せる**一方、**Vulkan backend は runner crash (SIGSEGV) を再現**した。
- `num_gpu` は「GPU枚数」ではなく**GPU offload層数**。現ログでは Vulkan 側は `num_gpu=0` のみ安定、`1/2/-1` は 500 失敗。
- `gfx900` は ROCm 7.x で公式既定サポート外だが、**残存コード経路・artifact・override運用**により条件付きで動作しうる。

## 3. 目的と到達点
### 目的
- Vega/gfx900 での Ollama / llama.cpp / ROCm / Vulkan の失敗条件を切り分ける。
- 「動くように見せる」ではなく、**比較可能な証跡**を残す。

### 到達点
- `num_gpu` 意味をコードで確定（offload層数）。
- ROCm vs Vulkan を同一条件で比較できるスクリプト/ログ形式を整備。
- gfx900 の「build target復活 / override運用 / runtime回避」事例を根拠URL付きで整理。

## 4. 重要な実験結果（最小セット）

| run_id | host | backend | 条件 | 結果 |
|---|---|---|---|---|
| `run_20260307_012643` | `11435` | ROCm | `num_gpu=0,1,2,-1`, `num_predict=512`, `qwen3.5:2b` | 全条件 `ok` |
| `run_20260307_013050` | `11434` | Vulkan | 同上 | `num_gpu=0` は `ok`、`1/2/-1` は `HTTP 500` + runner crash |
| `run_20260307_011230` | `11434` | Vulkan | `EPOCHS=3`, `NUM_GPU=0` | 3/3 `ok`（qwenスクリプト修正後） |
| `run_20260307_102504` | `11434` | Vulkan | 再検証 `EPOCHS=3`, `NUM_GPU=0` | 3/3 `ok`（エラー再発なし） |

補足:
- Vulkan 側 journal に `SIGSEGV` / `post predict ... EOF` を確認。
- ROCm 側 journal では同条件で `load_backend: ... libggml-hip.so`、`summary_by_num_gpu` 全 `ok`。

## 5. 技術的に確定したこと
### 5.1 `num_gpu` の意味
- `ollama-python -> ollama server -> runner -> llama.cpp` を追跡し、`num_gpu` は **offload層数**と確定。
- multi-GPU 枚数指定とは別概念。

### 5.2 crash の位相
- Vulkan crash は初期化失敗ではなく、**load完了後の compute 実行段階**（`computeBatch` 系）で発生。

### 5.3 gfx900 の位置づけ
- ROCm公式互換表では gfx900 非掲載（7.x 既定対象外）。
- 一方で、changelog/ソース/周辺実装には gfx900 残存経路がある。
- よって「公式保証外だが、条件次第で動く」は整合する。

## 6. 現実的な運用指針（現時点）
1. 再現性重視の比較では、ROCm/Vulkan を **同一条件**（model/prompt/epoch/num_predict/num_gpu）で固定する。
2. Vulkan 側の運用回避は `NUM_GPU=0`（必要なら `GGML_VK_VISIBLE_DEVICES=-1`）を優先。
3. gfx900 再有効化は、まず build target 明示（`AMDGPU_TARGETS` / `CMAKE_HIP_ARCHITECTURES`）から検証する。
4. `HSA_OVERRIDE_GFX_VERSION` は診断・暫定回避として扱い、恒久対策とは分ける。

## 7. すぐ再実行できるコマンド

```bash
cd /home/limonene/ROCm-project/vega-investigate
source .venv-test/bin/activate

# ROCm 比較
OLLAMA_HOST=http://127.0.0.1:11435 EPOCHS=1 NUM_PREDICT=512 NUM_GPU=0,1,2,-1 python vega-loop_qwen_rocm.py

# Vulkan 比較
OLLAMA_HOST=http://127.0.0.1:11434 EPOCHS=1 NUM_PREDICT=512 NUM_GPU=0,1,2,-1 python vega-loop_qwen_rocm.py

# qwen 単体安定確認（短縮）
EPOCHS=3 NUM_GPU=0 python vega-loop_qwen.py
```

## 8. ファイルインデックス

### 8.1 スクリプト
- `vega-loop.py`: tinyllama ループ基準。
- `vega-loop_qwen.py`: qwen 用（`EPOCHS`/`NUM_PREDICT`/`NUM_GPU` 環境変数対応）。
- `vega-loop_qwen_rocm.py`: ROCm/Vulkan 同形式比較用（失敗分類・backend probe・補助ログ採取）。

### 8.2 主要ランログ（`vega_work_log/`）
- `run_20260307_003423`: tinyllama baseline 成功。
- `run_20260307_010655`: qwen 500 再現（修正前/切り分け中）。
- `run_20260307_011230`: `EPOCHS=3` + `NUM_GPU=0` 成功。
- `run_20260307_011854`: Vulkan側で `num_gpu=0` のみ成功、`1/2/-1` 失敗。
- `run_20260307_012538`: ROCm側 `num_gpu=0,1,2,-1` 全成功（短縮条件）。
- `run_20260307_012643`: ROCm側 同一条件 (`num_predict=512`) でも全成功。
- `run_20260307_013050`: Vulkan側 同一条件で `1/2/-1` 失敗。
- `run_20260307_102504`: 再検証 `EPOCHS=3` 成功。

共通の主要ファイル:
- `result.json`（最重要）
- `ollama_journal_since_start.txt`（crash位相確認）
- `backend_probe.txt`（backend識別補助）
- `rocm_smi_*`, `ollama_ps_*`, `env.txt`, `meta.json`

### 8.3 調査レポート（`work_log/`）
- `work_log/debug_logs/20260307_010304_qwen_fail_investigation.md`
  - qwen失敗の時系列、修正、再検証ログ。
- `work_log/investigations/2026-03-07_numgpu_semantics_trace.md`
  - `num_gpu` 意味のコードトレース確定版。
- `work_log/investigations/2026-03-07_gfx900_gate_matrix.md`
  - gfx900 がどの層で block/allow されるかの行列。
- `work_log/investigations/2026-03-07_gfx900_existing_workarounds_matrix.md`
  - build target復活/override/runtime回避の事例表（URL付き）。
- `work_log/investigations/2026-03-07_0959_vega_rocm72_hypothesis.md`
  - ROCm公式系リポジトリ由来の仮説整理。
- `work_log/investigations/2026-03-07_1020_ollama_llamacpp_residual_paths.md`
  - Ollama/llama.cpp 側の残存経路初版。
- `work_log/investigations/2026-03-07_1043_numgpu_semantics_and_crash_phase_revision.md`
  - 上記の修正版（`num_gpu` 解釈修正 + crash位相明確化）。
- `work_log/hypothesis/2026-03-07_gfx900_reenable_steps.md`
  - 「戻す候補」の段階整理。
- `work_log/debug_logs/audit/2026-03-07_codex_minimal_scope_note.md`
  - 固定比較手順/採取ログ/判定項目の監査メモ。

## 9. 未確定事項（次フェーズ）
- Vulkan compute 経路のどのノード/条件で SIGSEGV になるか（更なるランタイム計測が必要）。
- `ollama` 配布artifactで gfx900 系 rocBLAS/Tensile がどこまで同梱されるか（版・ビルド系統差）。
- 未マージ patch/fork 手法を本流追従でどこまで代替できるか。

## 10. 最短の次アクション
1. 同一条件 (`qwen3.5:2b`, 固定prompt, `num_gpu=0,1,2,-1`) で ROCm/Vulkan を追加2セット回し、再現率を確定。
2. Vulkan失敗ケースだけ runner 側ログ粒度を上げ、`computeBatch` 以降のクラッシュ点を特定。
3. build target 明示の最小変更（`gfx900` 追加）を別ブランチで試し、`result.json` 互換形式で比較保存。
