# 調査レポート（2026-03-07 09:59 JST）: ROCm 7.2 で「本来サポート外の Vega(gfx900) が動く」理由の仮説

## 1. 調査目的
`/home/limonene/ROCm-project/tank/docs-ref/AMD_reference/AMD_Official/ROCm_AMD_Repo` 配下の公式系リポジトリを確認し、
「ROCm 7.2 で公式サポート対象外に見える Vega(gfx900) が、なぜ実際には動くケースがあるのか」を根拠付きで仮説化する。

## 2. 結論サマリ
- 現時点の一次情報からは、**「公式サポート外」=「完全に実行不能」ではなく、主に“リリース保証・QA・配布ターゲット外”**という意味で使われている可能性が高い。
- その一方で、ソース上には `gfx900` を依然扱う経路（アーキ定義・既存ロジック・テストマーカー）が残っており、**ワークロード依存で動作する余地**がある。
- したがって、Vega が 7.2 で動いた事象は、**「公式保証外だが、残存コードパス／ビルド設定次第で動作する」**で整合する。

## 3. 根拠（ファイルと行）

### 3.1 7.2 の互換性表では gfx900 が列挙されていない
- `ROCm/docs/compatibility/compatibility-matrix.rst:46-54`
  - 7.2.0 の GPU/LLVM target 一覧は `gfx950, gfx1201, gfx1200, gfx1101, gfx1100, gfx1030, gfx942, gfx90a, gfx908`。
  - `gfx900` がない。
- `ROCm/docs/compatibility/compatibility-matrix.rst:61-64,163`
  - 7.2.0 列で `llama.cpp` は `N/A`、脚注で `llama.cpp is only supported on ROCm 7.0.0 and 6.4.x` と記載。
- `ROCm/docs/release/versions.md:13`
  - 7.2.0 の公開日は **January 21, 2026**。

### 3.2 TheRock 側は「一部ターゲットのみ対応」と明言
- `TheRock/SUPPORTED_GPUS.md:5`
  - TheRock は将来リリース向けの開発状況であり、リリース版の公式対応は compatibility matrix を参照する旨。
- `TheRock/SUPPORTED_GPUS.md:19-46`
  - Linux 向け表に `gfx906` はあるが `gfx900` はない。
- `TheRock/cmake/therock_amdgpu_targets.cmake:47-74`
  - 定義開始は `gfx906` からで、`gfx900` のターゲット定義が見当たらない。
- `TheRock/RELEASES.md:81-92`
  - 配布インデックスの対象 `GFX Target` 一覧に `gfx900` がない。
- `rocm-libraries/CONTRIBUTING.md:306`
  - TheRock は「subset of AMD GPU targets」を現在サポートと記載。

### 3.3 「デフォルトでは外すが、明示指定でビルドは可能」という記述がある
- `ROCm/CHANGELOG.md:1786`
  - 該当セクションが ROCm 7.0.0。
- `ROCm/CHANGELOG.md:2232`
  - `gfx803` と `gfx900` は **no longer built by default**。
  - 必要なら `AMDGPU_TARGETS` で明示指定するよう記載。

### 3.4 一部ライブラリ側には gfx900 の残存サポート痕跡がある
- `rocm-libraries/shared/tensile/next-cmake/cmake/TensileSupportedArchitectures.cmake:32-35`
  - `BASE_ARCHITECTURES` に `gfx900` を含む。
- `rocm-libraries/projects/hipfft/CMakeLists.txt:75-92`
  - `DEFAULT_GPUS` に `gfx900` を含む。
- `rocm-libraries/projects/rocblas/library/src/blas3/Tensile/Logic/archive/vega10_Cijk_Alik_Bljk_SB.yaml:2-3`
  - `vega10` / `gfx900` 向けの archive logic が存在。
- `rocm-libraries/shared/tensile/pytest.ini:91,118`
  - `xfail-gfx900`, `skip-gfx900` マーカーが存在（=対象としては認識されているが、安定保証とは別）。

### 3.5 コンポーネントごとに移行速度が異なる形跡
- `ROCm/CHANGELOG.md:6425`
  - ここが ROCm 6.2.0 セクション。
- `ROCm/CHANGELOG.md:7563`
  - rocSOLVER では過去に `gfx900` を default build targets へ追加した履歴。
- 7.x 系では「デフォルト対象外化」記述もあり、**全コンポーネントで同時一律に切れたわけではない**ことが示唆される。

## 4. 仮説（確度付き）

### 仮説A（高確度）
**公式サポート外 = QA/配布/保証外であり、実行を強制的に禁止しているわけではない。**
- 互換性行列や TheRock の配布ターゲットには `gfx900` がない。
- しかし changelog 上は「デフォルトから外した」表現であり、明示指定ビルド余地が残る。

### 仮説B（高確度）
**Vega が動いたのは、使用した経路が“まだ gfx900 を保持する実装”に当たったため。**
- Tensile/hipFFT/rocBLAS のアーカイブロジック等に `gfx900` の痕跡がある。
- 単GPU・特定オペレーションでは動作しても、別機能（例: マルチGPU）では崩れる可能性が高い。

### 仮説C（中〜高確度）
**失敗条件（例: num_gpu>=2）は「Vega固有の未検証パス」に入った結果。**
- `skip/xfail-gfx900` が多数あることから、機能ごとに成熟度が不均一。
- そのため、同じ `gfx900` でも条件で成功/失敗が分かれやすい。

### 仮説D（中確度）
**実行環境のバイナリ由来差（どのターゲットでビルドされたか）が結果を左右。**
- 公式配布物は `gfx900` を含まない可能性が高い一方、ローカル/別経路で `gfx900` 含みのビルドが混在し得る。
- その場合「あるマシンでは動くが別環境では即死」が起きる。

## 5. 実務上の示唆（比較検証向け）
- 「動いた/落ちた」の比較時は、**サポート有無**とは別に、以下を固定採取すべき。
  - 実行バイナリが内包する amdgpu targets（`gfx900` を含むか）
  - 使用ライブラリ（hipBLAS/rocBLAS/Tensile）の実体とバージョン
  - 単GPUと複数GPUでの差分ログ
- つまり、今回の現象は「サポート外なのに動いた」より、
  **「サポート保証外の残存経路に乗ったため部分的に動いた」**と解釈するのが妥当。

## 6. 調査範囲の制約
- 本レポートは**リポジトリ記述の静的調査**に基づく。
- 実際に現在のローカル導入バイナリが `gfx900` を含んでいるかは、別途ランタイム検証が必要。
