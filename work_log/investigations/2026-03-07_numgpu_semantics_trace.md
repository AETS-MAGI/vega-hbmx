# 2026-03-07 num_gpu semantics trace

## 目的
- `num_gpu` の意味を、`ollama-python -> ollama server -> runner -> llama.cpp/include/llama.h` の実コードで確定する。
- 推測で `multi-GPU` と断定しないための根拠を固定化する。

## トレース結果（段階別）

| stage | file | line | interpretation | confidence |
|---|---|---:|---|---|
| 1. Pythonクライアント型 | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama-python/ollama/_types.py` | 104-110 | `Options` の「load time options」に `num_gpu` が定義される。推論実行中オプションではなくロード時オプション。 | High |
| 2. Pythonクライアント送信 | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama-python/ollama/_client.py` | 281-305 | `options` がそのまま `/api/generate` へ JSON として送られる。クライアント側で意味変換はしていない。 | High |
| 3. Ollama API型 | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/api/types.go` | 600-608 | `Runner` 構造体に `NumGPU` があり「model loaded into memory」のオプション群に属する。 | High |
| 4. Ollama既定値 | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/api/types.go` | 1071-1076 | 既定 `NumGPU=-1` は「動的に決める」意味。固定 GPU 枚数指定ではなく、オフロード量の自動決定文脈。 | High |
| 5. CLI説明 | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/cmd/interactive.go` | 112 | `num_gpu` は「GPUへ送る層数 (number of layers)」と明示。 | Very High |
| 6. サーバ割当 | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/llm/server.go` | 992 | `assignLayers(..., s.options.NumGPU, ...)` に `NumGPU` を `requestedLayers` として渡している。 | Very High |
| 7. 層割当ロジック | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/llm/server.go` | 1063-1076 | `requestedLayers` は `min(len(layers), requestedLayers)` で上限化される。変数の意味は層数。 | Very High |
| 8. runner変換 | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/runner/llamarunner/runner.go` | 906-925 | `numGPU += len(layers.Layers)` で合計層数を作り `NumGpuLayers` に渡す。GPUデバイス数を数えていない。 | Very High |
| 9. Go->Cブリッジ | `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/llama/llama.go` | 246-249, 264-267 | `ModelParams.NumGpuLayers` が `cparams.n_gpu_layers` に直結。 | Very High |
| 10. llama.cpp公開ヘッダ | `/home/limonene/ROCm-project/tank/docs-ref/llama/llama.cpp/include/llama.h` | 289 | `n_gpu_layers` は「VRAMに置く層数」、負値は全層。 | Very High |
| 11. llama.cpp共通パラメータ | `/home/limonene/ROCm-project/tank/docs-ref/llama/llama.cpp/common/common.h` | 382 | `-1 auto`, `<= -2 all` の意味が明示。 | Very High |

## 確定結論
- `num_gpu` は **GPU枚数ではなく、GPUへオフロードする層数**。
- `num_gpu>=2` をそのまま「multi-GPUに入った」と断定するのは不正確。
- `num_gpu` で変わるのはまず「層割当とオフロード経路」であり、複数GPU利用は別条件（デバイス列挙・割当結果）で決まる。

## 未確定（このトレース範囲外）
- どの条件で実際に複数デバイスに分散されるか（`assignLayers` の入力GPU集合・VRAM状況依存）。
- Vulkanクラッシュが層数増加でどのカーネル分岐に入って発生するか（要ランタイム追加計測）。
