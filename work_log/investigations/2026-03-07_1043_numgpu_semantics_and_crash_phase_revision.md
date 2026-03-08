# 調査レポート（2026-03-07 10:43 JST）: 指摘反映版（`num_gpu` 解釈修正 + クラッシュ時点切り分け + 実バイナリ確認）

## 0. この版で修正した点
- 旧仮説の「`num_gpu>=2` だから multi-GPU 経路に入る」という断定は撤回。
- `num_gpu` は **GPU枚数ではなく、GPU offload 層数（layers）** として扱うのが正しいことをコードで確認。
- Vulkan crash は「初期化時」よりも、**load完了後の推論実行（compute）中**に発生している証跡を明示。
- 実環境のインストール実体（`/usr/bin` 系と `/usr/local/bin` 系が並立）を確認し、`gfx900` 実体の所在を明示。

---

## 1. `num_gpu` の意味をコードで確定

### 1.1 クライアント/API層
- `ollama-python/ollama/_types.py:109`
  - `num_gpu` は load-time option。
- `ollama-python/ollama/_client.py:281-305`
  - `options` を `/api/generate` へ透過送信。
- `ollama/api/types.go:600-605`
  - Runner option に `NumGPU` / `MainGPU` がある。

### 1.2 Ollamaサーバ/配置ロジック
- `ollama/cmd/interactive.go:112`
  - ヘルプ文言が明示: `num_gpu` は「GPUへ送る層数」。
- `ollama/ml/backend.go:69-70`
  - `GPULayers` は「GPUへoffloadする層集合」。
- `ollama/llm/server.go:992`
  - `assignLayers(..., s.options.NumGPU, ...)` に `NumGPU` を requested layers として渡している。
- `ollama/llm/server.go:1063-1067`
  - `requestedLayers` として扱う実装。
- `ollama/llm/server.go:864-866`
  - `memory layout cannot be allocated with num_gpu = ...`（層割当失敗文脈）。

### 1.3 runner -> llama.cpp
- `ollama/llama/llama.go:266`
  - `cparams.n_gpu_layers = params.NumGpuLayers`。
- `llama.cpp/include/llama.h:289`
  - `n_gpu_layers` は「VRAMに置く層数」、負値は全層。
- `llama.cpp/common/common.h:382`
  - `n_gpu_layers`: `-1 auto`, `<= -2 all`。

### 1.4 結論（確定）
- `num_gpu` は「GPU枚数」ではなく「offload層数」。
- よって、`num_gpu>=2` 失敗を multi-GPU 断定で説明するのは不適切。

---

## 2. Vulkan crash が「どの段階か」を切り分け

対象ログ:
- `/home/limonene/ROCm-project/test_loop/vega_work_log/run_20260307_013050/ollama_journal_since_start.txt`

### 2.1 `num_gpu=0` は正常完走
- `:11` requested=0
- `:14,:18,:19` fit/alloc/commit
- `:26-28` offloaded 0/25
- `:31` `/api/generate` 200

### 2.2 `num_gpu=1` は load完了後に SIGSEGV
- `:41` requested=1
- `:44,:55,:60` fit/alloc/commit
- `:61-63` offloaded 1/25
- `:74` runner started
- `:75` `SIGSEGV`
- `:703-710` `ggml_backend_sched_graph_compute_async` -> `ComputeWithNotify` -> `runner.go:716 computeBatch`
- `:629-630` `post predict EOF` -> API 500

### 2.3 `num_gpu=2` でも同じ段階で落ちる
- `:663` requested=2
- `:666,:677,:682` fit/alloc/commit
- `:683-685` offloaded 2/25
- `:696` runner started
- `:697` `SIGSEGV`
- `:703-710` と同系統の compute stack
- `:1251-1252` `post predict EOF` -> API 500

### 2.4 `num_gpu=-1` でも同様
- `:1285` requested=-1
- `:1288,:1299,:1304` fit/alloc/commit
- `:1305-1307` offloaded 25/25
- `:1317` runner started
- `:1318` `SIGSEGV`
- `:1324-1331` compute stack（`ggml_backend_sched_graph_compute_async` -> `computeBatch`）
- `:1897-1898` `post predict EOF` -> API 500

### 2.5 結論（高確度）
- Vulkan crash は **初期化段階ではなく、モデルロード完了後の推論計算経路（computeBatch）** で発生。
- したがって、今回の主要因は「offload層数増加に伴って有効化されるVulkan計算経路の不安定性」と解釈するのが妥当。

---

## 3. 実バイナリに `gfx900` が入っているか

### 3.1 サービス実体が2系統ある
- `~/.config/systemd/user/ollama-rocm.service:7`
  - `ExecStart=%h/.local/bin/ollama-rocm-serve`
- `~/.config/systemd/user/ollama.service:7`
  - `ExecStart=/home/limonene/.local/bin/ollama-vega-vulkan serve`
- `/home/limonene/.local/bin/ollama-rocm-serve:4,12,33`
  - `/usr/bin/ollama` と `/usr/lib/ollama/libggml-hip.so` を前提。
- `/home/limonene/.local/bin/ollama-vega-vulkan:22`
  - `/usr/local/bin/ollama` を起動。

### 3.2 ROCm側の実体に `gfx900` artifact が存在
- `/usr/lib/ollama/rocblas/library/` に以下が存在することを確認:
  - `Kernels.so-000-gfx900.hsaco`
  - `TensileLibrary_*fallback_gfx900.hsaco`（複数）
- さらに実行ログ側でも `gfx900` 認識を確認:
  - `/home/limonene/ROCm-project/test_loop/vega_work_log/run_20260307_012538/ollama_journal_since_start.txt:25-26`
    - `ggml_cuda_init: found 1 ROCm devices`
    - `Device 0: AMD Radeon RX Vega, gfx900:xnack- ...`

### 3.3 Vulkan側は別バイナリ系統
- `/home/limonene/ROCm-project/test_loop/vega_work_log/run_20260307_013050/ollama_journal_since_start.txt:49,671,1293`
  - `load_backend: loaded Vulkan backend from /usr/local/lib/ollama/vulkan/libggml-vulkan.so`

### 3.4 結論
- この環境では「ROCm系 (`/usr/bin` + `/usr/lib/ollama`)」と「Vulkan系 (`/usr/local/bin` + `/usr/local/lib/ollama/vulkan`)」が並立。
- ROCm側には `gfx900` 向け実体（rocBLAS/Tensile hsaco）が実在し、これが「保証外だが動く」現象を強く補強する。

### 3.5 追補（2026-03-07 10:32 JST）
- `strings /usr/lib/ollama/libggml-hip.so | grep -i gfx900` で
  - `hipv4-amdgcn-amd-amdhsa--gfx900`
  を確認（ROCm HIPライブラリ内に gfx900 ターゲット文字列が存在）。
- `strings /usr/bin/ollama | grep -i 'ROCm|Vulkan|OLLAMA_VULKAN'` で
  - `Enable experimental Vulkan support`
  - `experimental Vulkan support disabled. To enable, set OLLAMA_VULKAN=1`
  - `ROCm`
  を確認（同一実体が backend 切替文脈を内包）。
- 以上より、「配布/実行環境で gfx900 経路が完全消滅していない」根拠は、ログだけでなく実体バイナリ文字列面でも補強できる。

---

## 4. 修正版の統合結論
- ROCm 7.2 での Vega/gfx900 動作は、公式保証外だが残存経路がある、という説明で整合する。
- `num_gpu` は GPU枚数ではなく offload層数なので、失敗条件は「multi-GPU断定」ではなく「offload層数依存の実行経路差」として扱うべき。
- 実測では、Vulkan側は `num_gpu>=1` でロード後 compute 中に `SIGSEGV`（`computeBatch`）を起こし、ROCm側は同条件で成功ケースを確認。
- したがって現時点の主因は、Vega一般より **Vulkan backend の offload計算経路不安定性** とみるのが最も安全で強い。

---

## 5. 旧仮説Cの置換（明示）
- 旧: `num_gpu>=2` は multi-GPU 経路が主因。
- 新（採用）:
  - `num_gpu>=2` 失敗の主要因は、multi-GPUそのものではなく、**GPU offload層数増加で有効化されるVulkan/HIP側の追加実行経路**の可能性が高い。
  - split / peer / sync は候補にはなるが、`num_gpu` 値だけで multi-GPU は断定しない。
