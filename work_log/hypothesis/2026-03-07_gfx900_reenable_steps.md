# 2026-03-07 gfx900 re-enable steps (候補整理のみ)

## 前提
- ここでは「戻す候補」を段階的に整理するのみ。広範囲パッチは未実施。
- 目的は「どの層が真のゲートか」を切り分けること。

## 1. build target を戻す場合

| target files | expected effect | risk | what it would prove if successful | recommended priority |
|---|---|---|---|---|
| `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/CMakeLists.txt` (`AMDGPU_TARGETS` default filter) | `ggml-hip` を `gfx900` でビルド対象化できる。 | 非推奨構成でビルド失敗/実行不安定。 | 「既定 CMake filter が主ゲートだった」ことを示せる。 | P1 |
| ビルド時引数 (`-DAMDGPU_TARGETS=gfx900` など) | ソース変更なしで filter bypass 可能。 | 依存ライブラリが `gfx900` 非対応ならリンク/実行失敗。 | コード変更なしで通れば、既定値由来のブロックを証明。 | P0 |

## 2. init validation を緩める場合

| target files | expected effect | risk | what it would prove if successful | recommended priority |
|---|---|---|---|---|
| `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/ml/device.go` (`NeedsInitValidation`, `AddInitValidation`) | discovery 時の deep init (`GGML_CUDA_INIT=1`) を緩和し、初期フィルタ除外を回避できる。 | unsupported GPU を通して runner が本番推論で crash しやすくなる。 | 「初期化フィルタが主ゲートだった」かを検証可能。 | P2 |
| `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/discover/runner.go` | init validation 失敗時の除外条件を一時変更して観測可能。 | 不安定構成を検出不能にしてしまう。 | validation の偽陰性/偽陽性の影響を定量化できる。 | P2 |

## 3. artifact / packaging を戻す場合

| target files | expected effect | risk | what it would prove if successful | recommended priority |
|---|---|---|---|---|
| `/usr/lib/ollama/rocblas/library` 配下の `*gfx900*` artifact 有無（実機検証） | `gfx900` 向け rocBLAS/Tensile code object の有無を確認できる。 | artifact 不整合で実行時クラッシュ/性能劣化。 | 「ビルドではなく配布物欠落が主因」かを証明できる。 | P0 |
| Ollama 側インストール処理 `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/CMakeLists.txt:158-163` | `rocblas` ディレクトリ同梱の有無が再現性に直結する。 | パッケージサイズ増、依存解決複雑化。 | artifact 搭載の有無で成功率が変われば packaging ゲートを示せる。 | P1 |
| TheRock 側 GPU family 設定 (`THEROCK_AMDGPU_FAMILIES` / `THEROCK_AMDGPU_TARGETS`) | 配布対象アーキに `gfx900` を含める実験設計が可能。 | サポート外ターゲットで CI/品質保証が崩れる。 | 上流パッケージ方針起因かを検証可能。 | P2 |

## 4. runtime/backend 側の追加調査が必要な場合

| target files | expected effect | risk | what it would prove if successful | recommended priority |
|---|---|---|---|---|
| `/home/limonene/ROCm-project/test_loop/vega_work_log/run_20260307_013050/ollama_journal_since_start.txt` と同条件再試験 | Vulkan crash が init 後 `computeBatch` 経路で起きる再現を固定できる。 | 追加計測コストのみ。 | 「Vega一般」ではなく「Vulkan実行経路」問題の強化。 | P0 |
| `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/runner/ollamarunner/runner.go` 周辺と ggml backend 呼出 | どの計算ノードで落ちるかを runner 側ログで特定可能。 | ログ増加によるノイズ。 | crash 点特定で、build/package ではなく runtime 実装要因を立証。 | P1 |
| Vulkan と ROCm を同一条件固定で比較（`model/prompt/num_gpu/epoch/num_predict` 完全一致） | backend差以外の変数を排除できる。 | 実行時間増。 | 因果の切り分け精度を上げられる。 | P0 |

## 推奨優先順（最小検証向け）
1. P0: 同一条件比較の固定運用 + artifact存在確認（非侵襲）
2. P1: build target override（引数レベル）
3. P2: init validation 緩和（最も副作用が大きいため後回し）

## 現時点の強い仮説（断定なし）
- `gfx900` は「公式既定の配布/ビルド対象」からは外されやすいが、artifact と backend 実装残存で条件付き動作する。
- 現在観測している fail は、`num_gpu` の層数増加で有効化される **Vulkan 実行経路** で顕在化しており、ROCm/HIP 側では同条件で再現していない。
