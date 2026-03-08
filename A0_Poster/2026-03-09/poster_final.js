const pptxgen = require("pptxgenjs");
const pres = new pptxgen();

// A0 portrait: 841mm × 1189mm = 33.11" × 46.81"
pres.defineLayout({ name: "A0", width: 33.11, height: 46.81 });
pres.layout = "A0";
pres.author = "Akira Ito";
pres.title = "Backend-Dependent Stability on Legacy HBM GPUs";

const s = pres.addSlide();
s.background = { color: "FFFFFF" };

// ===== COLORS (print-safe) =====
const RED = "B71C1C", BLUE = "0D47A1", GREEN = "1B5E20", ORANGE = "E65100";
const CARD = "F5F5F5", CARD2 = "EEEEEE", BDR = "BDBDBD", TXT = "212121", DIM = "616161";

// ===== LAYOUT =====
const W = 33.11, H = 46.81, M = 0.5, G = 0.4;
const CW = (W - 2*M - G) / 2; // ~16.105
const LX = M, RX = M + CW + G;

// ===== HELPERS =====
const mkSh = () => ({ type:"outer", blur:2, offset:1, angle:135, color:"000000", opacity:0.08 });

function hdr(x, y, w, num, title, col) {
  s.addShape(pres.shapes.OVAL, { x, y, w:0.9, h:0.9, fill:{color:col} });
  s.addText(num, { x, y, w:0.9, h:0.9, fontSize:32, fontFace:"Arial", color:"FFFFFF", bold:true, align:"center", valign:"middle" });
  s.addText(title, { x:x+1.05, y, w:w-1.05, h:0.9, fontSize:38, fontFace:"Arial Black", color:col, bold:true, valign:"middle", margin:0 });
}

function card(x, y, w, h) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill:{color:CARD}, shadow:mkSh() });
}

function bullets(x, y, w, h, items, sz) {
  const t = items.map((it, i) => {
    if (typeof it === "string") return { text:it, options:{ bullet:true, breakLine:i<items.length-1, fontSize:sz||22, color:TXT } };
    return { text:it.text, options:{ bullet:true, breakLine:i<items.length-1, fontSize:sz||22, color:it.color||TXT, bold:it.bold||false } };
  });
  s.addText(t, { x, y, w, h, fontFace:"Calibri", valign:"top", margin:[0.1,0.2,0.1,0.4] });
}

// ===== TITLE BAR =====
s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:W, h:4.5, fill:{color:RED} });
s.addShape(pres.shapes.RECTANGLE, { x:0, y:4.1, w:W, h:0.4, fill:{color:"7F1D1D"} });

s.addText("Backend-Dependent Stability on Legacy HBM GPUs", {
  x:M, y:0.3, w:W-2*M, h:1.8, fontSize:72, fontFace:"Arial Black", color:"FFFFFF", bold:true, align:"center", valign:"middle"
});
s.addText("ROCm/HIP vs Vulkan on Vega/gfx900: residual paths, offload-layer semantics, and reproducible diagnosis", {
  x:M, y:2.1, w:W-2*M, h:0.8, fontSize:32, fontFace:"Calibri", color:"FFCDD2", italic:true, align:"center", valign:"middle"
});
s.addText("Akira Ito  |  AETS (Akatsuki Enterprise Technology Solutions)  |  aets-giken@hiroshima-aktk.com", {
  x:M, y:2.9, w:W-2*M, h:0.6, fontSize:26, fontFace:"Calibri", color:"FFFFFF", align:"center", valign:"middle"
});
s.addText("IEICE GNW-68  |  Kyushu Sangyo University  |  March 9, 2026", {
  x:M, y:3.5, w:W-2*M, h:0.5, fontSize:22, fontFace:"Calibri", color:"FFCDD2", align:"center", valign:"middle"
});

// ===== LEFT COLUMN =====
let ly = 5.0;

// --- 1. Background & Motivation ---
hdr(LX, ly, CW, "1", "Background & Motivation", RED);
ly += 1.1;
card(LX, ly, CW, 3.6);
bullets(LX, ly, CW, 3.6, [
  "Official support matrices exclude gfx900 in ROCm 7.2, but real systems can still execute through residual code and artifact paths.",
  "For students and small labs, the key question is whether execution is possible, stable, and reproducible.",
  "We built a matched dual-backend testbed on the same Vega device to separate support policy, backend choice, and runtime behavior.",
  { text:'Goal: explain why "unsupported" and "unusable" are not the same statement.', bold:true },
]);
ly += 3.8;

// --- 2. Problem Statement ---
hdr(LX, ly, CW, "2", "Problem Statement", RED);
ly += 1.1;
card(LX, ly, CW, 3.0);
bullets(LX, ly, CW, 3.0, [
  "Legacy Vega GPUs are often treated as categorically unsuitable for modern ROCm workloads.",
  "Success or failure may be decided at different layers: distribution presets, build targets, init validation, backend macros, or runtime compute paths.",
  { text:"We ask: is instability caused by Vega itself, or by a specific backend path under matched conditions?", bold:true },
]);
ly += 3.2;

// --- 3. Related Work ---
hdr(LX, ly, CW, "3", "Related Work", BLUE);
ly += 1.1;

// 3A: LLNL
card(LX, ly, CW, 7.0);
s.addText([
  { text:"A. Numerical Divergence (LLNL, arXiv:2410.09172)", options:{ fontSize:26, bold:true, color:BLUE, breakLine:true } },
  { text:"Small self-contained tests expose cross-platform numeric differences.", options:{ fontSize:22, color:TXT, breakLine:true } },
], { x:LX+0.2, y:ly+0.15, w:CW-0.4, h:1.0, fontFace:"Calibri", valign:"top" });

s.addChart(pres.charts.BAR, [{
  name:"Divergence Rate", labels:["FP32 Direct","FP64 Direct","FP64 HIPIFY"], values:[9.00,0.98,1.10]
}], {
  x:LX+0.3, y:ly+1.3, w:CW-0.6, h:3.0, barDir:"col",
  showTitle:true, title:"NVIDIA vs AMD Numerical Divergence Rate (%)", titleColor:TXT, titleFontSize:20,
  chartColors:[RED,BLUE,ORANGE],
  chartArea:{ fill:{color:"FAFAFA"}, roundedCorners:true },
  catAxisLabelColor:DIM, catAxisLabelFontSize:18,
  valAxisLabelColor:DIM, valAxisLabelFontSize:16,
  valGridLine:{ color:"E0E0E0", size:0.5 }, catGridLine:{ style:"none" },
  showValue:true, dataLabelPosition:"outEnd", dataLabelColor:TXT, dataLabelFontSize:22, dataLabelFontBold:true,
  showLegend:false, valAxisMaxVal:10,
});
s.addText([
  { text:"Key insight: ", options:{ bold:true, color:ORANGE } },
  { text:"Compilation success does not guarantee equivalent behavior. This motivates backend-aware validation.", options:{ color:TXT } },
], { x:LX+0.2, y:ly+4.5, w:CW-0.4, h:2.2, fontSize:22, fontFace:"Calibri", valign:"top" });
ly += 7.2;

// 3B: Refutability / gem5
card(LX, ly, CW, 5.5);
s.addText([
  { text:"B. gem5 Vega Modeling (Univ. of Wisconsin-Madison)", options:{ fontSize:26, bold:true, color:BLUE, breakLine:true } },
  { text:"SE mode → GPUFS mode: real Linux kernel + unmodified amdkfd driver", options:{ fontSize:22, color:TXT } },
], { x:LX+0.2, y:ly+0.15, w:CW-0.4, h:1.0, fontFace:"Calibri", valign:"top" });

s.addChart(pres.charts.BAR, [{
  name:"Error (%)", labels:["Speedup (avg)","Speedup (worst)","Instr Count (avg)","Instr Count (worst)"], values:[6,10,6,7]
}], {
  x:LX+0.3, y:ly+1.3, w:CW-0.6, h:2.8, barDir:"col",
  showTitle:true, title:"gem5 vs Physical Vega 56: Simulation Error (%)", titleColor:TXT, titleFontSize:20,
  chartColors:[BLUE,"1976D2","00897B","00796B"],
  chartArea:{ fill:{color:"FAFAFA"}, roundedCorners:true },
  catAxisLabelColor:DIM, catAxisLabelFontSize:16,
  valAxisLabelColor:DIM, valAxisLabelFontSize:16,
  valGridLine:{ color:"E0E0E0", size:0.5 }, catGridLine:{ style:"none" },
  showValue:true, dataLabelPosition:"outEnd", dataLabelColor:TXT, dataLabelFontSize:22, dataLabelFontBold:true,
  showLegend:false, valAxisMaxVal:12,
});
s.addText("Vega architecture is well-characterized in academic simulation, establishing credibility as a research platform.", {
  x:LX+0.2, y:ly+4.3, w:CW-0.4, h:0.9, fontSize:22, fontFace:"Calibri", color:TXT, italic:true, valign:"top"
});
ly += 5.7;

// 3C: Support vs Residual
card(LX, ly, CW, 3.5);
s.addText("C. Support Matrices vs Residual Paths", {
  x:LX+0.2, y:ly+0.15, w:CW-0.4, h:0.6, fontSize:26, fontFace:"Arial", color:BLUE, bold:true
});

const spTblH = [
  { text:"Layer", options:{ fill:{color:BLUE}, color:"FFFFFF", bold:true, fontSize:20 } },
  { text:"Observation", options:{ fill:{color:BLUE}, color:"FFFFFF", bold:true, fontSize:20 } },
  { text:"Implication", options:{ fill:{color:BLUE}, color:"FFFFFF", bold:true, fontSize:20 } },
];
const spTblB = [
  [
    { text:"ROCm 7.2 matrix", options:{ fontSize:20, color:TXT, bold:true } },
    { text:"gfx900 not listed, not officially guaranteed", options:{ fontSize:20, color:TXT } },
    { text:"Support status alone does not decide runtime possibility", options:{ fontSize:20, color:TXT } },
  ],
  [
    { text:"Source / artifacts", options:{ fontSize:20, color:TXT, bold:true } },
    { text:"__gfx900__ paths, hsaco artifacts, HIP library strings remain", options:{ fontSize:20, color:TXT } },
    { text:"Residual paths can still enable partial execution", options:{ fontSize:20, color:TXT } },
  ],
];
s.addTable([spTblH, ...spTblB], {
  x:LX+0.2, y:ly+0.8, w:CW-0.4, border:{pt:1, color:BDR},
  colW:[(CW-0.4)*0.22, (CW-0.4)*0.42, (CW-0.4)*0.36],
  rowH:[0.45, 0.85, 0.85],
});
ly += 3.7;

// ===== RIGHT COLUMN =====
let ry = 5.0;

// --- 4. Engineering Challenges ---
hdr(RX, ry, CW, "4", "Engineering Challenges", ORANGE);
ry += 1.1;
card(RX, ry, CW, 3.6);
bullets(RX, ry, CW, 3.6, [
  "gfx900 is excluded by current official support matrices and default build filters, yet some code and artifacts still retain gfx900 handling.",
  { text:"`num_gpu` is easily misread as GPU count; code tracing shows it actually means offloaded layers.", bold:true },
  "The same Vega GPU can succeed on ROCm/HIP and fail on Vulkan under the same model and prompt.",
  "Diagnosis must be layer-by-layer and evidence-driven, not reduced to \"legacy GPU bad\".",
]);
ry += 3.8;

// --- 5. Engineering Interventions ---
hdr(RX, ry, CW, "5", "Evidence-First Investigation Strategy", ORANGE);
ry += 1.1;
card(RX, ry, CW, 5.6);
s.addText("Investigation Layers", {
  x:RX+0.2, y:ry+0.1, w:CW-0.4, h:0.5, fontSize:26, fontFace:"Arial", color:ORANGE, bold:true
});

const invH = [
  { text:"Layer", options:{ fill:{color:ORANGE}, color:"FFFFFF", bold:true, fontSize:20 } },
  { text:"Intervention", options:{ fill:{color:ORANGE}, color:"FFFFFF", bold:true, fontSize:20 } },
  { text:"Effect", options:{ fill:{color:ORANGE}, color:"FFFFFF", bold:true, fontSize:20 } },
];
const invB = [
  [
    { text:"L1: Distribution\n/ Build", options:{ fontSize:20, color:RED, bold:true } },
    { text:"Inspect support matrix, presets, target filters, installed artifacts", options:{ fontSize:20, color:TXT } },
    { text:"Locate where gfx900 is blocked, allowed, or only partially retained", options:{ fontSize:20, color:TXT } },
  ],
  [
    { text:"L2: API\nSemantics", options:{ fontSize:20, color:ORANGE, bold:true } },
    { text:"Trace `num_gpu` through client → server → runner → llama.cpp", options:{ fontSize:20, color:TXT } },
    { text:"Fix interpretation: offloaded layers, not GPU count", options:{ fontSize:20, color:TXT } },
  ],
  [
    { text:"L3: Runtime\nComparison", options:{ fontSize:20, color:BLUE, bold:true } },
    { text:"Run matched ROCm (:11435) and Vulkan (:11434) tests", options:{ fontSize:20, color:TXT } },
    { text:"Isolate backend-specific failure modes on identical hardware", options:{ fontSize:20, color:TXT } },
  ],
  [
    { text:"L4: Evidence\nCapture", options:{ fontSize:20, color:GREEN, bold:true } },
    { text:"Structured work logs, journal traces, backend probes, rocm-smi, ollama ps", options:{ fontSize:20, color:TXT } },
    { text:"Localize crashes and make claims reproducible", options:{ fontSize:20, color:TXT } },
  ],
];
s.addTable([invH, ...invB], {
  x:RX+0.2, y:ry+0.7, w:CW-0.4, border:{pt:1, color:BDR},
  colW:[(CW-0.4)*0.18, (CW-0.4)*0.45, (CW-0.4)*0.37],
  rowH:[0.45, 1.0, 1.0, 1.0, 1.0],
});

s.addText("Approach prioritizes falsifiable diagnosis and reproducibility over optimistic one-off success.", {
  x:RX+0.2, y:ry+4.8, w:CW-0.4, h:0.6, fontSize:22, fontFace:"Calibri", color:DIM, italic:true
});
ry += 5.8;

// --- 6. Experimental Results ---
hdr(RX, ry, CW, "6", "Experimental Results", GREEN);
ry += 1.1;

// Environment table
card(RX, ry, CW, 2.8);
s.addText("Test Environment", {
  x:RX+0.2, y:ry+0.1, w:CW-0.4, h:0.5, fontSize:24, fontFace:"Arial", color:GREEN, bold:true
});
const envH = [
  { text:"Component", options:{ fill:{color:GREEN}, color:"FFFFFF", bold:true, fontSize:20 } },
  { text:"Specification", options:{ fill:{color:GREEN}, color:"FFFFFF", bold:true, fontSize:20 } },
];
const envB = [
  [{ text:"GPU", options:{fontSize:20,color:TXT,bold:true} }, { text:"AMD Radeon RX Vega 56 (gfx900), 8 GB HBM2", options:{fontSize:20,color:TXT} }],
  [{ text:"OS / Kernel", options:{fontSize:20,color:TXT,bold:true} }, { text:"EndeavourOS, Kernel 6.12.74-1-lts", options:{fontSize:20,color:TXT} }],
  [{ text:"ROCm path", options:{fontSize:20,color:TXT,bold:true} }, { text:"Ollama 0.17.5 via :11435, library=ROCm, libggml-hip.so", options:{fontSize:20,color:TXT} }],
  [{ text:"Vulkan path", options:{fontSize:20,color:TXT,bold:true} }, { text:"Ollama 0.17.4 via :11434, library=Vulkan, same model/prompt", options:{fontSize:20,color:TXT} }],
];
s.addTable([envH, ...envB], {
  x:RX+0.2, y:ry+0.65, w:CW-0.4, border:{pt:1, color:BDR},
  colW:[(CW-0.4)*0.22, (CW-0.4)*0.78], rowH:[0.4, 0.4, 0.4, 0.4, 0.4],
});
ry += 3.0;

// Matched-Condition Verification
card(RX, ry, CW, 5.5);
s.addText("Matched-Condition Verification Results", {
  x:RX+0.2, y:ry+0.1, w:CW-0.4, h:0.5, fontSize:24, fontFace:"Arial", color:GREEN, bold:true
});
const vrH = [
  { text:"Stage", options:{ fill:{color:GREEN}, color:"FFFFFF", bold:true, fontSize:18 } },
  { text:"Verification", options:{ fill:{color:GREEN}, color:"FFFFFF", bold:true, fontSize:18 } },
  { text:"Evidence", options:{ fill:{color:GREEN}, color:"FFFFFF", bold:true, fontSize:18 } },
  { text:"Status", options:{ fill:{color:GREEN}, color:"FFFFFF", bold:true, fontSize:18 } },
];
const vrB = [
  [
    { text:"1. Support\nGate Check", options:{fontSize:18,color:TXT,bold:true} },
    { text:"Matrix / preset / artifact review", options:{fontSize:18,color:TXT} },
    { text:"gfx900 excluded from official matrix, but residual code and artifacts remain", options:{fontSize:18,color:TXT} },
    { text:"OK", options:{fontSize:20,color:GREEN,bold:true} },
  ],
  [
    { text:"2. API\nSemantics", options:{fontSize:18,color:TXT,bold:true} },
    { text:"`num_gpu` meaning trace", options:{fontSize:18,color:TXT} },
    { text:"client → server → llama.cpp shows offloaded layers, not GPU count", options:{fontSize:18,color:TXT} },
    { text:"OK", options:{fontSize:20,color:GREEN,bold:true} },
  ],
  [
    { text:"3. ROCm/HIP\nRun", options:{fontSize:18,color:TXT,bold:true} },
    { text:"qwen3.5:2b, num_gpu=0,1,2,-1", options:{fontSize:18,color:TXT} },
    { text:"All conditions succeeded under matched conditions (46-49s each)", options:{fontSize:18,color:TXT} },
    { text:"OK", options:{fontSize:20,color:GREEN,bold:true} },
  ],
  [
    { text:"4. Vulkan\nRun", options:{fontSize:18,color:TXT,bold:true} },
    { text:"Same model and parameters", options:{fontSize:18,color:TXT} },
    { text:"num_gpu=0 ok; num_gpu>=1 returned HTTP 500 (SIGSEGV)", options:{fontSize:18,color:TXT} },
    { text:"FAIL", options:{fontSize:20,color:RED,bold:true} },
  ],
  [
    { text:"5. Crash\nLocalization", options:{fontSize:18,color:TXT,bold:true} },
    { text:"journal / stack trace", options:{fontSize:18,color:TXT} },
    { text:"Load completed; SIGSEGV in computeBatch after runner start", options:{fontSize:18,color:TXT} },
    { text:"FAIL\n(Vulkan)", options:{fontSize:18,color:RED,bold:true} },
  ],
];
s.addTable([vrH, ...vrB], {
  x:RX+0.2, y:ry+0.65, w:CW-0.4, border:{pt:1, color:BDR},
  colW:[(CW-0.4)*0.14, (CW-0.4)*0.2, (CW-0.4)*0.5, (CW-0.4)*0.1],
  rowH:[0.4, 0.85, 0.85, 0.85, 0.85, 0.85],
});
ry += 5.7;

// Failure Diagnosis
card(RX, ry, CW, 4.0);
s.addText("Failure Diagnosis", {
  x:RX+0.2, y:ry+0.1, w:CW-0.4, h:0.5, fontSize:24, fontFace:"Arial", color:RED, bold:true
});
const fdH = [
  { text:"Hypothesis", options:{ fill:{color:"7B241C"}, color:"FFFFFF", bold:true, fontSize:20 } },
  { text:"Expected Evidence", options:{ fill:{color:"7B241C"}, color:"FFFFFF", bold:true, fontSize:20 } },
  { text:"Observed", options:{ fill:{color:"7B241C"}, color:"FFFFFF", bold:true, fontSize:20 } },
];
const fdB = [
  [
    { text:"Vega is generally\nunusable", options:{fontSize:20,color:TXT} },
    { text:"Both backends should fail on the same GPU", options:{fontSize:20,color:TXT} },
    { text:"Contradicted by ROCm/HIP success", options:{fontSize:20,color:GREEN,bold:true} },
  ],
  [
    { text:"`num_gpu` means\nGPU count", options:{fontSize:20,color:TXT} },
    { text:"Failure should imply multi-GPU entry", options:{fontSize:20,color:TXT} },
    { text:"Contradicted by code trace: it means offloaded layers", options:{fontSize:20,color:GREEN,bold:true} },
  ],
  [
    { text:"Vulkan compute\npath instability", options:{fontSize:20,color:ORANGE,bold:true} },
    { text:"Load completes; crash occurs after runner start in compute stack", options:{fontSize:20,color:TXT} },
    { text:"MATCH", options:{fontSize:22,color:RED,bold:true} },
  ],
];
s.addTable([fdH, ...fdB], {
  x:RX+0.2, y:ry+0.65, w:CW-0.4, border:{pt:1, color:BDR},
  colW:[(CW-0.4)*0.22, (CW-0.4)*0.4, (CW-0.4)*0.38],
  rowH:[0.4, 0.8, 0.8, 0.8],
});
ry += 4.2;

// Additional Finding
card(RX, ry, CW, 2.8);
s.addText("Why gfx900 Still Works Sometimes", {
  x:RX+0.2, y:ry+0.1, w:CW-0.4, h:0.5, fontSize:24, fontFace:"Arial", color:BLUE, bold:true
});
s.addText([
  { text:"ROCm 7.2 excludes gfx900 from official support, but changelog says ", options:{fontSize:20, color:TXT} },
  { text:'"no longer built by default"', options:{fontSize:20, color:ORANGE, bold:true} },
  { text:" rather than ", options:{fontSize:20, color:TXT} },
  { text:'"forbidden."', options:{fontSize:20, color:TXT} },
  { text:"\n\nIn the local ROCm install, gfx900 hsaco artifacts and `libggml-hip.so` strings were still present.", options:{fontSize:20, color:TXT, breakLine:true} },
  { text:"\n\nInterpretation: ", options:{fontSize:20, color:TXT, breakLine:true} },
  { text:"unsupported means unguaranteed and untested, not necessarily impossible to execute.", options:{fontSize:20, color:GREEN, bold:true} },
  { text:"\nThis explains why ROCm/HIP can run while Vulkan still fails on the same Vega card.", options:{fontSize:20, color:TXT} },
], { x:RX+0.2, y:ry+0.65, w:CW-0.4, h:2.0, fontFace:"Calibri", valign:"top", margin:[0.05,0.15,0.05,0.15] });
ry += 3.0;

// ===== FULL-WIDTH TAKEAWAY =====
const tkY = Math.max(ly, ry) + 0.3;
s.addShape(pres.shapes.RECTANGLE, { x:M, y:tkY, w:W-2*M, h:5.0, fill:{color:CARD}, shadow:mkSh() });

hdr(M+0.3, tkY+0.2, W-2*M-0.6, "7", "Takeaway & Key Messages", GREEN);

const mW = (W - 2*M - 1.2) / 3, mY = tkY + 1.4, mH = 3.2;
const msgs = [
  { icon:"✅", title:"Support Status ≠ Execution Reality", body:"Official exclusion does not imply absolute impossibility. Residual code paths, build targets, and shipped artifacts can still make gfx900 partially executable.", col:GREEN },
  { icon:"💡", title:"Backend Choice Dominates Stability", body:"On the same Vega/gfx900 device and the same model, ROCm/HIP passed fixed tests that Vulkan failed once GPU offload was enabled.", col:BLUE },
  { icon:"🔬", title:"Reproducibility Before Claims", body:"Gate matrices, code tracing, and matched work logs are necessary before declaring a legacy GPU \"dead\" or claiming a backend is stable.", col:ORANGE },
];

msgs.forEach((m, i) => {
  const mx = M + 0.3 + i * (mW + 0.3);
  s.addShape(pres.shapes.RECTANGLE, { x:mx, y:mY, w:mW, h:mH, fill:{color:CARD2}, shadow:mkSh() });
  s.addShape(pres.shapes.RECTANGLE, { x:mx, y:mY, w:mW, h:0.08, fill:{color:m.col} });
  s.addText(m.icon, { x:mx+0.2, y:mY+0.2, w:0.5, h:0.5, fontSize:28 });
  s.addText(m.title, { x:mx+0.8, y:mY+0.2, w:mW-1.0, h:0.6, fontSize:26, fontFace:"Arial", color:m.col, bold:true, valign:"middle" });
  s.addText(m.body, { x:mx+0.3, y:mY+0.9, w:mW-0.6, h:mH-1.1, fontSize:22, fontFace:"Calibri", color:TXT, valign:"top" });
});

// Footer
s.addText("Unsupported ≠ Impossible.  |  Legacy ≠ Poor.  |  Backend choice matters.", {
  x:M, y:H-0.7, w:W-2*M, h:0.5, fontSize:24, fontFace:"Calibri", color:DIM, italic:true, align:"center", valign:"middle"
});

// ===== WRITE =====
pres.writeFile({ fileName:"/home/claude/A0_Final_Poster.pptx" })
  .then(() => console.log("DONE"))
  .catch(e => console.error(e));
