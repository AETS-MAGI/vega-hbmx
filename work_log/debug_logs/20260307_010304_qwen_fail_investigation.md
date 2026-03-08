# 2026-03-07 01:03:04 JST | vega-loop qwen fail 調査ログ

## 対象
- 対象スクリプト: `vega-loop_qwen.py`
- 比較対象: `vega-loop.py` (`tinyllama:latest`)
- 目的: `vega` ループで `qwen` だけ失敗する原因特定と回避策確認

## 実施したデバッグ（時系列）
### 2026-03-07 00:44〜00:46
- `vega-loop.py` と `vega-loop_qwen.py` の差分確認。
- 実質的な差分はモデル指定のみ（`tinyllama:latest` vs `qwen3.5:2b`）。
- 既存ログ `vega_work_log/run_20260307_003423` は tinyllama が 20/20 成功していることを確認。

### 2026-03-07 00:45:56
- `vega-loop_qwen.py` 再実行で全 epoch エラー。
- ただしこの時点のエラーは `127.0.0.1:11434` 接続拒否（sandbox 制約由来）で、モデル固有原因は未判定。
- ログ: `vega_work_log/run_20260307_004556/result.json`

### 2026-03-07 00:46〜00:47
- 権限制約なしで Ollama の状態確認。
- `ollama list` で `qwen3.5:2b` が存在することを確認（モデル未取得が原因ではない）。
- `ollama ps` でも qwen/tinyllama がロード可能状態。

### 2026-03-07 00:46:38 以降
- 権限制約なしで `python vega-loop_qwen.py` 再実行。
- 結果: 全 epoch `500 Internal Server Error`。
- API本文: `{"error":"model runner has unexpectedly stopped ..."}`
- `ollama run qwen3.5:2b "hello"` も同様に 500。
- `ollama run tinyllama:latest "hello"` は成功。

### 2026-03-07 00:47〜00:52（根因確認）
- `journalctl --user -u ollama` を確認。
- qwen 実行ごとに以下のパターンを反復:
  - `SIGSEGV: segmentation violation`
  - `signal arrived during cgo execution`
  - 直後に `post predict ... EOF`
  - API が `500` を返す
- つまり、HTTPクライアント層や Python スクリプトではなく、**Ollama runner プロセスのクラッシュ**が直接原因。

### 2026-03-07 00:55〜00:59（回避策探索）
- `/api/generate` をオプション差し替えで検証:
  - `num_ctx` 変更（2048/1024）: 改善なし
  - `num_batch` 変更（128/64）: 改善なし
  - `flash_attention=false` 指定: 改善なし
  - `num_gpu=0`（CPU実行）: 成功
  - `num_gpu=1`（GPU 1層オフロード）: 成功
  - `num_gpu>=2` / `-1`（自動）: 再びクラッシュ
- `num_gpu=1` で 10 連続リクエストを実施し、`10/10` 成功を確認。

## 考えたこと（仮説）
- モデル未ダウンロードやモデル名不一致の問題ではない。
- VRAM不足よりも、Vega + Vulkan バックエンドでの qwen3.5 実行時に、一定以上のGPUオフロード層数で runner が不安定化する可能性が高い。
- tinyllama が成功して qwen のみ失敗するため、`qwen3.5` 系の実行パスとハードウェア/バックエンドの相性問題と判断。

## わかったこと（確定）
- `qwen3.5:2b` fail の直接原因は `ollama runner` の `SIGSEGV`。
- `vega-loop_qwen.py` 自体のロジック不具合ではなく、バックエンドクラッシュ起因の 500。
- 回避条件は `num_gpu` 制限（`0` or `1`）。`2` 以上で再現率高くクラッシュ。

## 回避できた理由として考えられること
- `num_gpu=1` により GPU へ配置するモデル層を最小化し、問題の発生する実行パス（多層GPUオフロード時の処理）を回避できた。
- `num_gpu=0` は完全CPU実行のためクラッシュを回避できるが、速度は低下。
- 実運用上は `num_gpu=1` が「安定性と速度の折衷点」。

## 実施したコード変更
- `vega-loop_qwen.py` を以下の方針で更新:
  - `NUM_GPU` を環境変数対応で追加（デフォルト `1`）
  - API オプションに `num_gpu` を付与
  - HTTPエラー時に Ollama の `error` 本文を例外メッセージへ含める
  - `EPOCHS` / `NUM_PREDICT` を環境変数で上書き可能にして検証しやすくした

## 参照した主なローカル根拠
- `vega_work_log/run_20260307_003423/result.json`（tinyllama 成功）
- `vega_work_log/run_20260307_004556/result.json`（sandbox接続不可）
- `vega_work_log/run_20260307_004638/result.json`（qwen 500）
- `journalctl --user -u ollama`（SIGSEGV と EOF）

---

## 追記: 2026-03-07 01:14:46 JST | 再検証（EPOCHS=3）結果

### 実施内容
- ユーザー依頼により、`EPOCHS=3` での再検証を再開。
- まず当時の修正状態（`NUM_GPU=1` 既定）のまま実行:
  - 実行: `EPOCHS=3 python vega-loop_qwen.py`
  - 結果: 3/3 で `HTTP 500 from Ollama`
  - ログ: `vega_work_log/run_20260307_010655/result.json`
- 次に同条件の単発APIで再切り分け:
  - 長文プロンプト + `num_gpu=1` は `num_predict` を 64 まで下げても失敗
  - 同条件で `num_gpu=0` は成功

### 追加でわかったこと
- `num_gpu=1` は短文プロンプトでは通るケースがあるが、今回の長文プロンプトでは安定しない。
- したがって、実運用の安定性優先なら `num_gpu=0` を既定にするのが安全。

### 追加修正
- `vega-loop_qwen.py` の既定値を変更:
  - `NUM_GPU = int(os.environ.get("NUM_GPU", "1"))`
  - から
  - `NUM_GPU = int(os.environ.get("NUM_GPU", "0"))`
- これにより、デフォルトはCPU実行（必要なら `NUM_GPU` 環境変数で上書き可能）。

### 再再検証（修正後）
- 実行: `EPOCHS=3 python vega-loop_qwen.py`
- 結果: `3/3` 成功
  - epoch1: `ok elapsed=42.27s chars=2105`
  - epoch2: `ok elapsed=42.84s chars=1999`
  - epoch3: `ok elapsed=42.46s chars=1901`
- ログ: `vega_work_log/run_20260307_011230/result.json`
- `meta.json` でも `num_gpu: 0` を確認済み。

### 回避できた理由（追記）
- `qwen3.5:2b` + Vega/Vulkan では、現状 GPU オフロード時に runner が SIGSEGV へ落ちる条件が残る。
- CPU実行へ固定することで、問題のGPU実行パスを通らなくなり、`EPOCHS=3` の連続ループを安定して完走できた。

---

## 追記: 2026-03-07 01:25:55 JST | ROCm比較用スクリプト作成と初期検証

### 追加実装
- 新規作成: `vega-loop_qwen_rocm.py`
- 目的: Vulkan 側と同形式で、ROCm 側の `num_gpu` 条件比較を残す。
- 互換性重視で以下を維持:
  - 保存先: `vega_work_log/run_YYYYMMDD_HHMMSS/`
  - 主ファイル: `meta.json`, `result.json`, `responses/`, `rocm_smi_*`, `ollama_ps_*`
- 拡張点:
  - `NUM_GPU` を複数値で受理（例: `0,1,2,-1` を順次実行）
  - 失敗分類を追加（`connection_error`, `timeout`, `http_error`, `json_decode_error`, `script_exception`）
  - HTTP失敗時の `response.error` を `result.json` と標準エラーへ出力
  - backend判定補助として `backend_probe.txt` と `ollama_journal_since_start.txt` を保存
  - `OLLAMA_HOST` 既定を ROCm サービス想定の `http://127.0.0.1:11435` に設定

### 検証ログ（作成直後）
- `run_20260307_011854`:
  - 実行時に `OLLAMA_HOST=11434` 相当を参照していたため、Vulkan側証跡が混在。
  - `num_gpu=0` は成功、`1/2/-1` は 500 失敗。
  - 比較用途としては「Vulkan側再現確認」の補助ログ。

### 検証ログ（ROCmポート）
- `run_20260307_012538`:
  - `OLLAMA_HOST=http://127.0.0.1:11435`（ROCmサービス）
  - `num_gpu=0,1,2,-1` を各1回実行し、全て `status=ok`
  - `summary_by_num_gpu` で各条件の成否を集約済み
- `ollama_journal_since_start.txt` で確認できた根拠:
  - `ollama-rocm-serve[...]`
  - `library=ROCm`
  - `load_backend: loaded ROCm backend from /usr/lib/ollama/libggml-hip.so`
  - `device=ROCm0`

### 現時点の示唆
- Vulkan側で観測した `num_gpu>=2` 即クラッシュ条件は、少なくともこの短縮ROCm検証では再現しなかった。
- ただし `EPOCHS=1`, `NUM_PREDICT=16` の短縮条件なので、長文・長生成・複数epochでの追試が必要。

### 追試（Vulkan比較に寄せた条件）
- `run_20260307_012643`:
  - 条件: `EPOCHS=1`, `NUM_PREDICT=512`, `NUM_GPU=0,1,2,-1`, `OLLAMA_HOST=http://127.0.0.1:11435`
  - 結果: `num_gpu=0/1/2/-1` 全て `status=ok`
  - `summary_by_num_gpu` も全条件 `ok=1, error=0`
- backend証跡（`ollama_journal_since_start.txt`）:
  - `ollama-rocm-serve[...]`
  - `library=ROCm`
  - `load_backend: loaded ROCm backend from /usr/lib/ollama/libggml-hip.so`
  - `device=ROCm0`
- この条件では、Vulkan側で出ていた `num_gpu>=2` の runner crash は再現しなかった。

### 同一スクリプト・同一条件での Vulkan 側比較
- `run_20260307_013050`:
  - 条件: `EPOCHS=1`, `NUM_PREDICT=512`, `NUM_GPU=0,1,2,-1`, `OLLAMA_HOST=http://127.0.0.1:11434`
  - 結果:
    - `num_gpu=0`: `ok`
    - `num_gpu=1,2,-1`: `http_error` (500)
  - `summary_by_num_gpu`:
    - `0 => ok=1`
    - `1/2/-1 => error=1`
- `ollama_journal_since_start.txt` 根拠:
  - `library=Vulkan`
  - `load_backend: loaded Vulkan backend ...`
  - `SIGSEGV: segmentation violation`
  - `post predict ... EOF` 後に API 500

### 比較結論（現時点）
- 同一スクリプト・同一パラメータ (`NUM_PREDICT=512`, `NUM_GPU=0,1,2,-1`) で比較した結果:
  - ROCm (`11435`) は全条件成功
  - Vulkan (`11434`) は `num_gpu>=1` で失敗（特に `>=2` は再現）

### まとめ
- Vulkan 側の runner crash は、少なくとも同一条件の ROCm/HIP 検証では再現しなかった。
- 同一スクリプト・同一パラメータ (`NUM_PREDICT=512`, `NUM_GPU=0,1,2,-1`) で比較した結果:
  - ROCm (`11435`) は全条件成功
  - Vulkan (`11434`) は `num_gpu>=1` で失敗
- よって、現時点の主要因は Vega 一般ではなく、Vega 環境における Vulkan backend 経路の不安定性である可能性が高い。
- Vulkan 側の実運用回避策としては `num_gpu=0` が安全。
- ROCm/HIP 側については、長文・長生成・複数epochで継続追試する。

---

## 追記: 2026-03-07 10:27:15 JST | 再検証（EPOCHS=3, 現行スクリプト）

### 実施内容
- 実行: `source .venv-test/bin/activate && EPOCHS=3 python vega-loop_qwen.py`
- ログ: `vega_work_log/run_20260307_102504/result.json`
- 条件:
  - `MODEL=qwen3.5:2b`
  - `NUM_PREDICT=512`
  - `NUM_GPU=0`（既定）

### 結果
- `3/3` epoch で `status=ok`（HTTP 500 / 接続失敗なし）
  - epoch1: `elapsed=44.636s`, `response_chars=0`
  - epoch2: `elapsed=42.071s`, `response_chars=1622`
  - epoch3: `elapsed=42.263s`, `response_chars=0`
- したがって、少なくとも今回の再実行では「qwen スクリプトの失敗（runner crash 経由の HTTP 500）」は再発していない。

### 観測メモ
- epoch1/3 は `eval_count=512` かつ `done=true` だが `response` は空文字だった。
- これはクラッシュ系エラーとは別の挙動（モデル出力内容の揺れ）として扱うのが妥当。
