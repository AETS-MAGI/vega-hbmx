# vega-hbmx-experiments 査読ノート

査読日: 2026-03-24
方針: 疑義・誤り・証拠不足・内部矛盾のみ記載。正確な記述は記録しない。

---

## 総評

このディレクトリは全体的に品質が高い。

- 旧仮説（multi-GPU 説）は修正版（offload 層数説）へのリンクと「改訂注記」が入っており、透明度が高い
- ほぼすべての主張がコード行番号または `run_id` で参照可能
- 「未確定」「可能性」「留保」の表記が一貫して使われている
- audit-log.md で発表前の自己修正プロセスも記録されている

以下の指摘は「著しい誤り」ではなく、将来参照時に注意が必要な細部。

---

## 1. phi4-mini の速度比較：eval_count の差が未考慮

**ファイル**: `A0_Poster/2026-03-09/発表前追い込み実験結果.md`（行142）

```
phi4-mini num_gpu=0 (18.82s, 318 tok) vs num_gpu=1 (31.55s, 512 tok)
→ GPU offload 時の速度向上は限定的または誤差範囲
```

**問題点**: 2つの run で eval_count が異なる（318 vs 512）。絶対時間を直接比較すると「GPU offload が遅い」印象になるが、実際のスループットは：

- num_gpu=0: 318 / 18.82 ≈ **16.9 tok/s**
- num_gpu=1: 512 / 31.55 ≈ **16.2 tok/s**

ほぼ同値であり、「速度向上なし」という結論は正しいが、「GPU offload が遅い（絶対時間が長い）」という読み方は誤り。絶対時間の差はほぼ生成トークン量の差（318→512）で説明される。

また、なぜ num_gpu=0 で eval_count が 512 ではなく 318 で止まったか（stop token hit か truncation か）が不明。これが tok/s 計算の基準として適切かは要確認。

「速度向上は限定的」という結論自体は正しく、`tok/s` で比較すれば読み取れるが、発表資料に使う場合は tok/s の比較として明示した方が正確。

---

## 2. analysis_summary.md の "unknown" backend が未定義

**ファイル**: `analysis_summary.md`（行22-24）

```
| unknown | 0 | 6 | 0 | 6 | 100% | 42.76s | ±0.96s |
| unknown | 1 | 0 | 3 | 3 | 0% | — | — |
| unknown | ? | 0 | 40 | 40 | 0% | — | — |
```

`unknown` backend が何を指すか本ファイル内で説明されていない。40件の `num_gpu=?` も含めると 49 レコード（全体の約40%）が `unknown` に分類されているが、その由来（ログ解析スクリプトが backend を特定できなかったケースか、記録自体が欠落していたケースか）が不明。

発表資料でこの集計を引用する場合、`unknown` の内訳が読者に伝わらない。

---

## 3. gate_matrix.md が参照している ollama のパスが現在の構成と異なる

**ファイル**: `work_log/investigations/2026-03-07_gfx900_gate_matrix.md`（行12-14）

gate_matrix は `/home/limonene/ROCm-project/tank/docs-ref/llama/ollama/` 配下のリファレンスコピーを参照している。特に行13での rocBLAS artifact の観測は `/usr/lib/ollama/rocblas/library` を指している。

この調査は 2026-03-07 時点のもので、当時は system ollama（`/usr/lib/ollama`）を実験に使っていた。現在の MI25/gfx900 フォーク構成では：

- ollama バイナリ: `ollama-src/ollama`（フォーク）
- rocBLAS library: `ROCBLAS_TENSILE_LIBPATH` で AETS fork path を注入
- `librocblas.so.5` 本体: `/opt/rocm-7.2.0/lib/`（system）

gate_matrix が示す構成とは異なる。このファイルは初期調査の snapshot として有効だが、現在の構成の説明として引用すると誤解を招く。本ファイル自体には時点が明記されているので問題はないが、cross-reference 時に注意が必要。

---

## 4. ROCm 実験全条件 ok の解釈に関する留保（補足）

**ファイル**: `A0_Poster/2026-03-09/発表前追い込み実験結果.md`（行108）

```
ROCm（override-assisted）: 2日・2バージョンにわたり 8/8 全条件 ok
```

この「ROCm 全条件 ok」は `HSA_OVERRIDE_GFX_VERSION=9.0.0` および `ollama-manual.sh` 等で設定される環境変数がすべて適切に設定された状態での結果である。audit-log.md が指摘（行34）したように `HSA_OVERRIDE_GFX_VERSION=9.0.0` は再現性に重要であり、これは発表資料に反映済みとのこと。

一方、「ROCm ok = GPU で実行した」という意図があるとすれば、実際にどのレイヤーで実行されているか（GPU offload か CPU fallback か）は `GPULayers` ログ等で確認が必要。本ディレクトリの実験では `num_gpu` を offload 層数として制御しており、`num_gpu=0` が「GPU offload なし」を意味することが README に記載されている。ただし 2026-03-07 時点の ROCm 実験では `num_gpu=0,1,2,-1` いずれでも ok となっており、「ok = GPU 実行」とは必ずしも言えない。

本質的には発表の主張が「ROCm は crash しない（qwen3.5:2b において）」なのか「ROCm は GPU を使って速い」なのかによって解釈が変わる。前者なら問題なく、後者なら GPU 実行の確認が必要。

---

## 要約テーブル

| # | ファイル | 問題の種類 | 重大度 |
|---|---|---|---|
| 1 | 発表前追い込み実験結果.md | phi4-mini 速度比較で eval_count 差が未考慮 | 低（発表精度に影響） |
| 2 | analysis_summary.md | "unknown" backend 49件の定義・由来が不明 | 低 |
| 3 | gfx900_gate_matrix.md | 参照先が current AETS fork 構成と異なる（snapshot の位置づけは明確） | 低（注意点） |
| 4 | 発表前追い込み実験結果.md | ROCm "ok" が GPU 実行を意味するかは未確認（発表主張次第） | 低（主張の範囲次第） |
