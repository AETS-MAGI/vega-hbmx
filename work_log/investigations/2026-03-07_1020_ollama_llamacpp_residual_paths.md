# 調査レポート（2026-03-07 10:20 JST）: Ollama / llama.cpp における Vega(gfx900) 残存経路と `num_gpu>=2` 失敗仮説

> 改訂注記: `num_gpu` の意味をコード追跡で再検証した結果、「GPU枚数」ではなく「GPU offload層数」であることが確認された。  
> この初版にある multi-GPU 断定仮説は、改訂版 `2026-03-07_1043_numgpu_semantics_and_crash_phase_revision.md` で置換済み。

## 1. 目的
- 対象:
  - `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama`
  - `/home/limonene/ROCm-project/tank/docs-ref/llama/llama.cpp`
  - `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama-python`
- 目的:
  - 「本来サポート外扱いの Vega/gfx900 がなぜ動く場合があるか」を、実装・ビルド・配布の観点で根拠付きで整理する。
  - 併せて `num_gpu>=2` での失敗条件について、根拠ベースで強い仮説を作る。

## 2. 結論サマリ
- 事実として、**Ollama の配布/既定ビルドは gfx900 を積極的に対象外化**している。
- ただし同時に、**ソース実装には gfx900 系マクロ・HIP経路・override運用の残存経路**があり、ワークロード次第で動く余地が残っている。
- `num_gpu>=2` 失敗は、**offload層数増加で有効化される追加実行経路（split/peer/sync を含む可能性）**が主要因である可能性が高い。
- つまり「公式サポート外」と「完全に実行不能」は一致しておらず、
  **配布対象外 + 残存実装経路 + 条件依存で部分動作**という構図が最も整合的。

## 3. 具体的な残存経路（事実）

### 3.1 ドキュメント上の「非公式だが試行可能」経路
- `ollama/docs/gpu.mdx:81-89`
  - ROCm は全GPUをサポートしないが、`HSA_OVERRIDE_GFX_VERSION` で試せる旨を明記。
- `ollama/docs/gpu.mdx:95-108`
  - Linux 既知サポートLLVM target一覧に `gfx900` は含まれない。
- `llama.cpp/docs/build.md:369`
  - 公式サポート外GPU向けに `HSA_OVERRIDE_GFX_VERSION` を案内。

解釈:
- 公式保証外でも実行余地を残す運用を、両プロジェクトとも明示している。

### 3.2 ビルドターゲットの絞り込み経路（配布側）
- `ollama/CMakePresets.json:72-77`
  - `ROCm 6` preset の `AMDGPU_TARGETS` に `gfx900` は含まれない。
- `ollama/CMakeLists.txt:125-128`
  - `AMDGPU_TARGETS` 未指定時、`^gfx(94[012]|101[02]|1030|110[012]|120[01])$` のみ採用。
- `ollama/Dockerfile:88`
  - `rocblas/library/*gfx90[06]*` を削除。
- `ollama/scripts/build_windows.ps1:210`
  - `*gfx906*` の rocBLAS library を削除。

解釈:
- 公式成果物レベルでは古い gfx9 系を外す方向が強い。

### 3.3 それでもソース内に gfx900 残存経路がある
- `ollama/ml/backend/ggml/ggml/src/ggml-cuda/vendors/hip.h:173-175`
  - `__gfx900__` / `__gfx906__` を `GCN5` として扱うマクロ。
- `ollama/ml/backend/ggml/ggml/src/ggml-cuda/common.cuh:609-623`
  - `__gfx900__` 向け分岐（`dp4a` 経路）を保持。
- `llama.cpp/ggml/src/ggml-cuda/vendors/hip.h:174-176`
  - upstream 側でも同様に `__gfx900__` 分岐を保持。

解釈:
- 「完全削除」ではなく、実装遺産/互換経路が継続している。

### 3.4 Ollama が「unsupported で落ちる前提」で初期化フィルタを入れている
- `ollama/ml/device.go:535-542`
  - `NeedsInitValidation()` が ROCm/CUDA を要検証扱い。
- `ollama/ml/device.go:539`
  - コメント: ROCm は unsupported device で rocBLAS crash の可能性。
- `ollama/ml/device.go:545-547`
  - `AddInitValidation()` で `GGML_CUDA_INIT=1` を付与。
- `ollama/discover/runner.go:121-123,146-153`
  - 2nd pass で device ごとに deep init 検証。
- `ollama/discover/runner.go:460-462`
  - unsupported AMD を除外中の runner exit は想定内と明記。
- `ollama/llm/server.go:391-392`
  - unsupported device crash を避けるため常時フィルタする旨。
- `ollama/ml/backend/ggml/ggml/src/ggml-cuda/ggml-cuda.cu:271-276`
  - `GGML_CUDA_INIT` 時に `rocblas_initialize()`。
  - コメントで unsupported GPU だと `SIGABRT` と明記。

解釈:
- プロジェクト自身が「unsupported でクラッシュし得る」前提をコード化している。

### 3.5 `num_gpu>=2` で有効化されうる経路（分割/peer/sync）が複雑
- `ollama/runner/llamarunner/runner.go:910-927`
  - `Devices`, `NumGpuLayers`, `TensorSplit` を load 時に構成。
- `ollama/ml/backend/ggml/ggml/src/ggml-cuda/ggml-cuda.cu:1507-1560`
  - device 間 peer access の enable/disable 制御。
- `ollama/ml/backend/ggml/ggml/src/ggml-cuda/ggml-cuda.cu:2954-2958`
  - backend 間コピーで peer copy を使用（`GGML_CUDA_NO_PEER_COPY` なら不可）。
- `ollama/ml/backend/ggml/ggml/src/ggml-cuda/ggml-cuda.cu:1762-1786`
  - split + 複数device 時に event/sync を使う同期経路。
- `ollama/ml/backend/ggml/ggml/src/ggml-cuda/ggml-cuda.cu:2235-2237,2260-2262`
  - split buffer では一部 fusion 最適化を無効化（TODO残存）。
- `ollama/CMakeLists.txt:138-140`
  - Windows でのみ `GGML_CUDA_NO_PEER_COPY` を定義。Linux ROCm では既定で peer copy 経路が有効。

解釈:
- `num_gpu` は offload層数指定であり、GPU枚数そのものを意味しない。
- ただし offload層数が増えると split/peer/sync 等の追加経路が有効化され、失敗条件を作る可能性が高い。

### 3.6 llama.cpp 側も同じ構造を持つ
- `llama.cpp/ggml/src/ggml-hip/CMakeLists.txt:31-37`
  - `AMDGPU_TARGETS` -> `GPU_TARGETS` -> `CMAKE_HIP_ARCHITECTURES` を受け渡し。
- `llama.cpp/ggml/CMakeLists.txt:201`
  - `GGML_CUDA_NO_PEER_COPY` オプションあり（既定OFF）。
- `llama.cpp/ggml/src/ggml-cuda/ggml-cuda.cu:650-654`
  - 異デバイスコピーで peer copy 経路。

解釈:
- Ollama 特有というより、下層 ggml の HIP/CUDA 設計由来の性質を引き継いでいる。

### 3.7 ollama-python の位置づけ
- `ollama-python/ollama/_types.py:109-110`
  - `num_gpu`, `main_gpu` は options として定義。
- `ollama-python/ollama/_client.py:281-305`
  - `/api/generate` に options を透過送信するクライアント。

解釈:
- `ollama-python` 自体は backend 判定ロジックを持たず、サーバ側（Ollama/ggml）が本質。

## 4. 「なぜ Vega が動くことがあるか」の強い仮説

### 仮説A（高確度）
**配布ターゲット外でも、ソース上の gfx900 残存経路 + 手元ビルド条件で実行可能性が残る。**
- 根拠: 3.2 と 3.3 が同時に成立。
- 推論: 「非推奨・非保証」と「実行不能」は別。

### 仮説B（高確度）
**初期化検証を通る範囲の処理は動くが、モデル/設定次第で runtime 経路が変わり失敗する。**
- 根拠: 3.4（deep init フィルタ）と 3.5（offload層数依存の複雑経路）。
- 推論: 単GPU成功と高offload失敗の分離を説明可能。

### 仮説C（中〜高確度）
**`num_gpu>=2` 失敗の主要因は、offload層数増加で有効化される追加実行経路の不安定性。**
- 根拠: 3.5, 3.6。
- 推論: `num_gpu=0/1` 成功かつ `>=2` 失敗という現象パターンと整合。
- 注記: `num_gpu` 値だけで multi-GPU は断定しない。

### 仮説D（中確度）
**実行バイナリに含まれる amdgpu target / rocBLAS artifact の差分が環境依存の成否を作る。**
- 根拠: 3.2（artifact除去） + 3.3（実装残存）。
- 推論: 「ある環境でだけ動く」を説明可能。

## 5. 現時点で未確定な点
- コード読解だけでは、`qwen3.5:2b` + `num_gpu>=2` のクラッシュ箇所を1点に断定できない。
- とくに以下は runtime 証跡が必要:
  - SIGABRT 発生位置（rocBLAS init か、推論中 peer/split か）
  - 失敗時の `ollama ps` / server stderr / dmesg / ROCm runtime log

## 6. 次に取るべき検証（短期）
1. `num_gpu=0,1,2,-1` で同一モデル・同一プロンプト・同一エポックの再現ログを固定フォーマットで比較。
2. `OLLAMA_DEBUG=1` と runner stderr 採取で、`GGML_CUDA_INIT` 周辺と load 後のどちらで落ちるか分離。
3. 可能なら `GGML_CUDA_NO_PEER_COPY=1` 相当ビルド/設定で A/B 比較し、offload経路失敗への寄与を切り分け。
4. 実行バイナリのターゲット同定（含まれる gfx arch と rocBLAS artifact）を環境ごとに記録。

---

### 注記
- 本レポートはリポジトリ静的調査に基づく。
- 「高確度」はコード上の因果整合が強いことを意味し、実機での最終断定ではない。
