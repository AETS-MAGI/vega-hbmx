# 2026-03-07 gfx900 gate matrix

## 目的
- `gfx900` がどの層で落とされうるかを、配布・ビルド・初期化・実行時で表にして比較可能にする。
- 「どこで block / allow / partial か」を断定ではなく根拠つきで整理する。

## ゲート行列

| layer | file | current handling of gfx900 | blocks / allows / partial | evidence lines | notes |
|---|---|---|---|---|---|
| 配布 preset | `/home/limonene/ROCm-project/tank/docs-ref/AMD_reference/AMD_Official/ROCm_AMD_Repo/ROCm/docs/compatibility/compatibility-matrix.rst` | ROCm 7.2.0 の GPU/LLVM target 一覧に `gfx900` は記載されず、`gfx908/90a/...` が列挙される。 | blocks (公式サポート観点) | `compatibility-matrix.rst:46-55` | 公式互換表上は非掲載。ただし「非掲載=絶対不可」までは示していない。 |
| CMake target filter | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/CMakeLists.txt` | `AMDGPU_TARGETS` 未指定時、正規表現 `^gfx(94[012]|101[02]|1030|110[012]|120[01])$` にフィルタされるため `gfx900` は既定対象外。 | blocks (default) / allows (manual override) | `CMakeLists.txt:125-128` | `AMDGPU_TARGETS` を明示すれば別経路は残る。 |
| rocBLAS artifact | `/home/limonene/ROCm-project/test_loop` 実機環境 + `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/CMakeLists.txt` | 実機 `/usr/lib/ollama/rocblas/library` に `Kernels.so-000-gfx900.hsaco` など `gfx900` 向けアーティファクトが存在。Ollama CMake も `rocblas` ディレクトリをインストール対象にしている。 | allows / partial | `CMakeLists.txt:158-163` + filesystem evidence (`/usr/lib/ollama/rocblas/library/*gfx900*`) | 配布物に含まれていれば実行余地が残る。欠落すればここで実質 block。 |
| runner init validation | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/ml/device.go` + `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/discover/runner.go` | ROCm/CUDA デバイスは `NeedsInitValidation=true`。`GGML_CUDA_INIT=1` を付けて深い初期化を行い、初期化失敗デバイスは discovery で除外される。 | partial (fail時に block) | `device.go:535-547`, `runner.go:121-153`, `runner.go:183-185`, `runner.go:461-462` | 「起動できるか」の関門。通れば実行段階へ進む。 |
| backend macro | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/ml/backend/ggml/ggml/src/ggml-cuda/vendors/hip.h` + `.../common.cuh` | `__gfx900__` を `GCN5` として扱う分岐が存在し、`ggml_cuda_dp4a` でも `__gfx900__` 向け実装分岐がある。 | allows (compile path) / partial (性能・安定性は別) | `hip.h:173-175`, `common.cuh:609-623` | ソース上は完全削除されていない。 |
| runtime crash point | `/home/limonene/ROCm-project/test_loop/vega_work_log/run_20260307_013050/ollama_journal_since_start.txt` + `result.json` 比較 | Vulkan ではロード後に `computeBatch` 経路で SIGSEGV。ROCm 比較ランでは同条件 (`num_gpu=0,1,2,-1`) が成功。 | partial (backend-dependent) | `ollama_journal_since_start.txt:41-75`, `:703-710`, `:629-630`; `run_20260307_013050/result.json:47-88`; `run_20260307_012643/result.json:47-113` | block点は「Vega一般」より「Vulkan実行経路」に寄る可能性が高い。 |

## 補足
- 追加の配布系根拠として、ROCm changelog には「`gfx803` と `gfx900` はデフォルトビルド対象から外れた。必要なら `AMDGPU_TARGETS` 明示」とある。  
  - `/home/limonene/ROCm-project/tank/docs-ref/AMD_reference/AMD_Official/ROCm_AMD_Repo/ROCm/CHANGELOG.md:2232`
- したがって現状は「公式既定は外す方向」だが「実装・配布残存経路があれば条件付きで通る」の二層構造になっている。
