# Audit Log: Poster Content Review

Date: 2026-03-08
Target: `A0_Poster/2026-03-09/poster_final.js`
Reviewer action: 調査資料との整合監査 + 生成JSの刷新

## 1) 判定

**判定: 旧版ポスター内容は一部不適切（修正が必要）**

理由:
- 調査ログで裏付けていない外部研究データ（数値グラフ）を、主要根拠に近い位置で提示していた。
- backend失敗の説明で、条件依存（`num_gpu=0` の Vulkan 成功例）より一般化した印象を与える構成だった。
- 「公式サポート外」「実行可能性」「安定性」の3層が混在し、読者が断定的に受け取りやすい構図だった。

## 2) 監査で参照した主資料

- `README.md`
- `work_log/investigations/2026-03-07_1043_numgpu_semantics_and_crash_phase_revision.md`
- `vega_work_log/run_20260307_012643/result.json`（ROCm matched条件）
- `vega_work_log/run_20260307_013050/result.json`（Vulkan matched条件）

## 3) JS刷新内容（実施済み）

- 旧版の外部研究セクション（LLNL/gem5の図表）を削除。
- 本リポジトリの調査で再現できる事実のみで再構成。
- 以下を明示する構成へ変更:
  - `num_gpu` の意味（offload layers）
  - matched-condition run結果
  - Vulkanの失敗位相（load後 computeBatch / SIGSEGV）
  - 「unsupported ≠ impossible」ただし「保証外は保証外」の注意
- 出力先をローカル相対パス化:
  - `A0_Poster/2026-03-09/A0_Final_Poster_revised.pptx`

## 4) 監査後の妥当性

改訂版は、現在の調査範囲に対して以下を満たす:
- 主張と証跡の対応関係が明確
- 強い断定を避け、条件・限界を併記
- 再実行コマンドを併記し、再現性を担保

