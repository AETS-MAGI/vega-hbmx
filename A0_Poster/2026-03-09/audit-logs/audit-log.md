# Poster Audit Log — 2026-03-08

## Audit Trigger
Codex code review identified three structural issues in the poster prior to printing.

## Issues Found

### Issue 1: External research graphs without repo-backed evidence
- **Problem:** LLNL divergence chart (arXiv:2410.09172) and gem5 simulation error chart were displayed as primary evidence. These are external publications not replicated or verified in this repository.
- **Severity:** Misleading — conflates cited literature with own experimental results.
- **Resolution:** Remove both charts. Replace Related Work section with repo-backed findings: gfx900 gate matrix and num_gpu semantics trace. External references retained as text citations only.

### Issue 2: Over-generalization of Vulkan failure
- **Problem:** Poster implied Vulkan fails categorically on Vega. In reality, Vulkan succeeds with `num_gpu=0`. Failure is specific to `num_gpu>=1`.
- **Severity:** Inaccurate claim scope.
- **Resolution:** All Vulkan failure claims now explicitly state the condition: "num_gpu>=1". The num_gpu=0 success is shown in results.

### Issue 3: Missing run_id traceability
- **Problem:** Experimental results did not cite specific run IDs.
- **Severity:** Reproducibility gap.
- **Resolution:** Key results now reference: `run_20260307_012643` (ROCm all OK), `run_20260307_013050` (Vulkan num_gpu>=1 fail).

## Evidence Sources (repo-internal only)
- `work_log/investigations/2026-03-07_gfx900_gate_matrix.md`
- `work_log/investigations/2026-03-07_numgpu_semantics_trace.md`
- `work_log/investigations/2026-03-07_1043_numgpu_semantics_and_crash_phase_revision.md`
- `work_log/debug_logs/20260307_010304_qwen_fail_investigation.md`
- `vega_work_log/run_20260307_012643/result.json`
- `vega_work_log/run_20260307_013050/result.json`

## Revision 3 (2026-03-08 post-review)

### Added (P0 — mandatory before print)
1. **HSA_OVERRIDE_GFX_VERSION=9.0.0** added to Test Environment table (was missing — critical for reproducibility)
2. **Vulkan version note** added: "0.17.4 vs 0.17.5 is inherent to dual-install; both tested as-shipped"
3. **Limitations & Future Work** section added before Takeaway (was completely absent)
4. **Related Literature** expanded from 2 to 4 items (added SDMA workaround + HSA_OVERRIDE context)

### Added (P1 — important for accuracy)
5. **Model dependency** noted: tinyllama succeeded on Vulkan (run_20260307_003423, 20/20 OK); qwen3.5 triggers SIGSEGV
6. **response_chars=0** noted as model output quirk, not crash
7. **"within tested scope"** qualifier added to ROCm success claims in both results note and Takeaway

### Added (P2 — completeness)
8. **tinyllama run_id** (run_20260307_003423) added to Reproducibility takeaway
9. **Future Work** items: multi-epoch tests, additional models, ROCm version comparison, GGML_CUDA_NO_PEER_COPY experiments

### Output
- `A0_Final_Poster_revised.pptx` — print-ready A0, all text ≥18pt
- `poster_final_revised.js` — regeneration source
