# gfx900 (Vega) 既存 workaround 事例マトリクス (2026-03-07)

## 3分類サマリ
- build target 復活: 5件（公式/本流コード2、issue/fork recipe 2、RFC 1）。`AMDGPU_TARGETS` / `CMAKE_HIP_ARCHITECTURES` に `gfx900` を明示して再ビルドする系。
- override 運用: 4件（公式docs 1、issue 2、discussion 1）。`HSA_OVERRIDE_GFX_VERSION` による実行時マスク/擬似適合化。
- runtime 回避: 6件（公式docs 2、本流コード3、issue 1）。`ROCR_VISIBLE_DEVICES` / `GGML_VK_VISIBLE_DEVICES` / init validation / peer-copy抑制 / artifact除外 / ROCmバージョン回避。

注意:
- 「gfx900を有効化したコード変更」と「環境変数で通した運用」を分離して分類した。
- fork/issue のパッチは未マージ前提で扱い、`directly reusable` は最小限に限定した。

## 既存事例一覧

| category | project | type | title | URL or reference | date | what it changes | how gfx900 is handled | evidence snippet (要約) | usefulness for our case | risk / limitation | confidence | reusable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| build target 復活 | ROCm | changelog | gfx803/gfx900 をデフォルト対象から外し、明示 target 指定を要求 | https://github.com/ROCm/ROCm/blob/1aeb3c0df1524b4a96febb086fcb212b388696ed/CHANGELOG.md#L2232 | 2026-02-18 (file update) | 既定ビルド対象を縮小 | `AMDGPU_TARGETS=gfx900` を明示すればビルド可能であることを示唆 | 変更履歴で「no longer built by default」「specify explicitly」を明記 | 「なぜ保証外でも動くか」の一次根拠になる | ROCm全体の方針であり、ollama単体の成功を保証しない | high | partially reusable |
| build target 復活 | llama.cpp/ggml | build config | ggml-hip が AMDGPU_TARGETS/GPU_TARGETS を CMAKE_HIP_ARCHITECTURES に転送 | https://github.com/ggml-org/llama.cpp/blob/c024d859082183bc4e9446e0a56c8299b23def0f/ggml/src/ggml-hip/CMakeLists.txt#L31-L37 | 2026-01-29 (file update) | HIPアーキ指定の伝搬 | `-DAMDGPU_TARGETS=gfx900` を渡す経路が本流に存在 | CMakeで forward し `enable_language(HIP)` へ接続 | 最小変更でgfx900再ビルド可否を検証できる | 実行時ライブラリ/rocBLAS整合が別途必要 | high | directly reusable |
| build target 復活 | ollama | preset | ROCm preset に AMDGPU_TARGETS を持つ（現行既定は gfx900 非含有） | https://github.com/ollama/ollama/blob/e790dc435b148933da3b98b423397bf022e38104/CMakePresets.json#L72-L78 | 2026-02-03 (file update) | Ollama runner のHIP build target を固定 | 既定一覧に gfx900 は無いので、追加patchで再有効化対象 | ROCm 6 preset に target list がハードコード | Vulkan/ROCm比較のための再ビルド入口として有用 | 既定から外れているため保守対象外寄り | high | partially reusable |
| build target 復活 | ollama | issue + patch | "Comprehensive Workaround for AMD RX Vega 64 ..." | https://github.com/ollama/ollama/issues/12303 | 2025-09-16 (opened) | `CMAKE_HIP_ARCHITECTURES` や supported_types 等を patch | issue本文差分で `gfx900` を target/supported list に追加 | body diff に `AMDGPU_TARGETS ... gfx900:xnack-` や supported_types追加がある | そのまま検証用パッチ候補として使える | 未マージissue。環境依存が強く、将来壊れる可能性高 | medium | partially reusable |
| build target 復活 | ollama (fork) | fork + build recipe | likelovewant/ollama-for-amd (ROCm5系) | https://github.com/likelovewant/ollama-for-amd/wiki/How-to-Compile-ollama-for-AMD-GPU | 2025-11頃 (検索スニペット: “Published 4 months ago”) | forkでAMD向けビルド手順を提供 | `-DAMDGPU_TARGETS="gfx803;gfx900:xnack-"` 等を使う手順が提示 | wiki手順で gfx900 明示 build を案内 | 既存運用ノウハウの参照価値あり | fork未マージ。本流乖離・ROCm7系非保証 | medium | reference only |
| override 運用 | ollama | official docs | Overrides on Linux (`HSA_OVERRIDE_GFX_VERSION`) | https://github.com/ollama/ollama/blob/e790dc435b148933da3b98b423397bf022e38104/docs/gpu.mdx#L79-L93 | 2026-01-31 (file update) | unsupported AMD GPU に override を案内 | gfx非対応時に近傍targetを偽装して試行 | docsで「unsupported AMD GPU can experiment」と明記 | 既存環境で即試せる最小回避 | 恒久解ではなく誤動作/性能低下の余地 | high | directly reusable |
| override 運用 | ollama | issue | Vega64で `HSA_OVERRIDE_GFX_VERSION` 運用報告 | https://github.com/ollama/ollama/issues/8772 | 2024-07-15 (opened) | systemd環境変数でoverrideを適用 | `HSA_OVERRIDE_GFX_VERSION=10.3.0` 運用例 | issue本文で override 設定と `ollama ps` 結果が共有 | 実運用ログ付きで再現条件設計に使える | 単一報告で再現保証はない | medium | partially reusable |
| override 運用 | llama.cpp | discussion | ROCm build/実行時に override を併用した報告 | https://github.com/ggml-org/llama.cpp/discussions/7867 | 2024-06-11 (opened) | build flags + env override の併用例 | `HSA_OVERRIDE_GFX_VERSION=11.0.0` 実行例が記載 | discussion内で `-DAMDGPU_TARGETS` と override の試行が記述 | ollama配下runnerの下層(ggml/hip)挙動の参照になる | 成功事例というより試行ログ。機種がgfx900限定ではない | medium | reference only |
| override 運用 | ollama (fork) | wiki recipe | fork wiki の `HSA_OVERRIDE_GFX_VERSION` 運用手順 | https://github.com/likelovewant/ollama-for-amd/wiki/How-to-Compile-ollama-for-AMD-GPU | 2025-11頃 (検索スニペット: “Published 4 months ago”) | unsupported GFX向けに実行時overrideを設定 | `HSA_OVERRIDE_GFX_VERSION=9.0.0` を例示して回避運用 | wiki要約に「set `HSA_OVERRIDE_GFX_VERSION=9.0.0` if some gpus are not detected」 | Vega/gfx900 の実運用ヒントとして使える | fork未マージ、wiki本文の将来変更/消失リスク | medium | reference only |
| runtime 回避 | ollama | official docs | ROCm GPU選択/CPU強制 (`ROCR_VISIBLE_DEVICES`) | https://github.com/ollama/ollama/blob/e790dc435b148933da3b98b423397bf022e38104/docs/gpu.mdx#L117-L121 | 2026-01-31 (file update) | 可視GPUを限定、`-1` でCPU強制 | 問題GPUを迂回して実行可能 | docsで subset 指定と invalid ID fallback を明記 | 比較試験で条件固定・切り分けに直結 | 性能低下 or GPU未使用になる | high | directly reusable |
| runtime 回避 | ollama | official docs | Vulkan GPU無効化 (`GGML_VK_VISIBLE_DEVICES=-1`) | https://github.com/ollama/ollama/blob/e790dc435b148933da3b98b423397bf022e38104/docs/gpu.mdx#L163-L167 | 2026-01-31 (file update) | Vulkan backend を実行時に停止 | Vulkan crash回避しROCm/HIP比較を維持 | docsで問題時の disable を明示 | 今回の「Vulkanで落ちる」条件切り分けに最適 | Vulkan経路の検証自体はできなくなる | high | directly reusable |
| runtime 回避 | ollama | source code | init validation で unsupported GPU を先に落とす | https://github.com/ollama/ollama/blob/e790dc435b148933da3b98b423397bf022e38104/ml/device.go#L535-L547 | 2025-12-12 (file update) | `GGML_CUDA_INIT=1` を設定し deep init | rocBLAS crashリスクGPUを事前検知する意図 | コメントに「rocblas will crash on unsupported devices」 | Pythonバグとbackend crashの区別に有効 | 検知で落ちるので「通す」回避ではない | high | partially reusable |
| runtime 回避 | ollama | source code | peer copy回避定義 (`GGML_CUDA_NO_PEER_COPY`) | https://github.com/ollama/ollama/blob/e790dc435b148933da3b98b423397bf022e38104/CMakeLists.txt#L138-L140 | 2026-02-05 (file update) | ggml-hip build時にpeer copy無効化（Windows条件） | peer copy関連経路を抑止する設計意図 | CMakeで `target_compile_definitions(... GGML_CUDA_NO_PEER_COPY)` | peer/split仮説の検証観点に合う | Linuxでは既定で有効でない。直接流用は追加patchが必要 | medium | reference only |
| runtime 回避 | ollama | packaging recipe | Docker buildで gfx90[06] rocBLAS artifact を除去 | https://github.com/ollama/ollama/blob/e790dc435b148933da3b98b423397bf022e38104/Dockerfile#L88 | 2026-03-06 (file update) | 配布物から特定arch向けrocBLAS kernelsを削除 | gfx900/gfx906 を配布で実質無効化 | Dockerfileに `rm ... rocblas/library/*gfx90[06]*` | 「なぜバイナリで動かないか」の強い説明材料 | 回避というより除外。再有効化には再パッケージ必須 | high | reference only |
| runtime 回避 | ROCm | issue | バージョン固定による回避 (6.4.1で通る/6.4.3で失敗) | https://github.com/ROCm/ROCm/issues/5229 | 2025-03-13 (opened) | runtime stack差分で回避 | gfx900(Vega64)で版依存の成功/失敗がある | issueで ROCmバージョン差による挙動差が報告 | 再現検証時の比較軸として有効 | 根治でなく回避。別版で再発し得る | medium | partially reusable |
| build target 復活 | TheRock (ROCm関連) | RFC / packaging design | Multi-Arch Packaging RFC に gfx900 shard/package を明記 | https://github.com/ROCm/TheRock/blob/f6d8e210abf0c00fad53adcce5d27a5337305212/docs/rfcs/RFC0008-Multi-Arch-Packaging.md#L63-L83 | 2025-11-20 (file update) | arch別 artifact 分割設計を提案 | gfx900 build/artifact を設計上は想定 | RFCで `gfx900-build` や `rocm-device-libs-gfx900` 例示 | artifact復活戦略の設計参考になる | RFC段階。本番配布で保証されない | medium | reference only |

## 今の環境で試す価値が高い順 (Top 5)
1. `llama.cpp/ggml` と `ollama` の build target 明示 (`AMDGPU_TARGETS` / `CMAKE_HIP_ARCHITECTURES` に `gfx900`) を同一条件で再ビルドして比較する。  
   根拠: 本流CMake経路が存在し、再現性の高い検証ができる。
2. `HSA_OVERRIDE_GFX_VERSION=9.0.0` (必要ならGPUごとの `_0` 形式) を使った override 運用を ROCm backend のみで固定比較する。  
   根拠: ollama公式docs + 実運用issueがある。
3. Vulkan切り分けとして `GGML_VK_VISIBLE_DEVICES=-1`（または `OLLAMA_VULKAN` 無効）で ROCm/HIP と Vulkan を明確に分離する。  
   根拠: 公式docsに明記、今回のクラッシュ切り分けに直結。
4. 配布artifact差分を確認し、`rocblas/library/*gfx90[06]*` 除去の有無を検証する。  
   根拠: Dockerfileで除去が実装されており、動作差の主要因候補。
5. ROCm版差比較（例: 6.4.1系 vs 6.4.3系 / 現在7.x系）を最小ケースで行う。  
   根拠: ROCm issueで版依存が報告されている。

## 未確定事項
- `ollama/ollama#12303` の提案パッチが本流に取り込まれたか、部分取り込みかは未確定。
- `likelovewant/ollama-for-amd` の wiki手順が ROCm 7.x / 現在の ollama HEAD で有効かは未検証。
- `num_gpu>=2` 失敗の主因が multi-GPU か offload層数増加かは、コード引数追跡と実測の突合せがまだ必要。
- Vulkan crash点（初期化時 vs 推論中）の境界は、runner側ログ増強なしでは断定不可。
- 配布済みバイナリに実際どのgfx向け rocBLAS/Tensile artifact が含まれるかは、個別ビルド成果物の実体確認が必要。

## 次に人間が判断すべきこと
1. 本流追従を優先するか、fork/未マージpatchを許容してでも検証速度を優先するか。
2. まず固定する比較軸を「backend差(ROCm vs Vulkan)」に置くか、「ROCm版差」に置くか。
3. `HSA_OVERRIDE_GFX_VERSION` を常用前提にするか、あくまで一時的診断手段に限定するか。
4. artifact復活（gfx900向け rocBLAS/Tensile）を試す際に、ローカル再パッケージを許容するか。
5. 失敗許容範囲（クラッシュ許容の検証環境）と、運用環境で求める安定条件をどこで分けるか。
