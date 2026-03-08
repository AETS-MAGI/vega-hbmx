const pptxgen = require('pptxgenjs');
const pres = new pptxgen();

pres.defineLayout({ name: 'A0', width: 33.11, height: 46.81 });
pres.layout = 'A0';
pres.author = 'Akira Ito';
pres.title = 'Vega/gfx900 Backend Investigation (Evidence-Only Revision)';

const s = pres.addSlide();
s.background = { color: 'FFFFFF' };

const C = {
  red: 'B71C1C',
  blue: '0D47A1',
  green: '1B5E20',
  orange: 'E65100',
  gray: 'F5F5F5',
  line: 'BDBDBD',
  txt: '212121',
  dim: '616161',
};

const W = 33.11;
const H = 46.81;
const M = 0.55;
const G = 0.45;
const CW = (W - (2 * M) - G) / 2;
const LX = M;
const RX = M + CW + G;

function header(x, y, w, num, title, color) {
  s.addShape(pres.shapes.OVAL, { x, y, w: 0.75, h: 0.75, fill: { color } });
  s.addText(num, {
    x,
    y,
    w: 0.75,
    h: 0.75,
    align: 'center',
    valign: 'middle',
    bold: true,
    color: 'FFFFFF',
    fontFace: 'Arial',
    fontSize: 24,
  });
  s.addText(title, {
    x: x + 0.9,
    y,
    w: w - 0.9,
    h: 0.75,
    color,
    bold: true,
    fontFace: 'Arial Black',
    fontSize: 28,
    valign: 'middle',
    margin: 0,
  });
}

function panel(x, y, w, h) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x,
    y,
    w,
    h,
    radius: 0.08,
    line: { color: C.line, pt: 1 },
    fill: { color: C.gray },
  });
}

function bulletBox(x, y, w, h, lines, fs = 20) {
  const runs = lines.map((t, i) => ({
    text: t,
    options: { bullet: true, breakLine: i < lines.length - 1, fontSize: fs, color: C.txt },
  }));
  s.addText(runs, {
    x,
    y,
    w,
    h,
    fontFace: 'Calibri',
    valign: 'top',
    margin: [0.08, 0.12, 0.08, 0.28],
  });
}

// Title
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 3.5, fill: { color: C.red }, line: { color: C.red } });
s.addText('Vega/gfx900: ROCm と Vulkan の安定性比較（証跡ベース改訂版）', {
  x: M,
  y: 0.38,
  w: W - (2 * M),
  h: 1.2,
  align: 'center',
  valign: 'middle',
  color: 'FFFFFF',
  bold: true,
  fontFace: 'Arial Black',
  fontSize: 52,
});
s.addText('主張を「調査で確認できた事実」のみに限定。推測・外部比較・未検証引用を削除。', {
  x: M,
  y: 1.85,
  w: W - (2 * M),
  h: 0.7,
  align: 'center',
  valign: 'middle',
  color: 'FFCDD2',
  italic: true,
  fontFace: 'Calibri',
  fontSize: 24,
});
s.addText('Data date: 2026-03-07 logs / 2026-03-08 summary', {
  x: M,
  y: 2.6,
  w: W - (2 * M),
  h: 0.45,
  align: 'center',
  color: 'FFFFFF',
  fontFace: 'Calibri',
  fontSize: 18,
});

let ly = 3.9;
let ry = 3.9;

// Left column
header(LX, ly, CW, '1', '評価基準（何を妥当とみなすか）', C.red);
ly += 0.9;
panel(LX, ly, CW, 4.5);
bulletBox(LX + 0.18, ly + 0.18, CW - 0.36, 4.1, [
  '同一条件比較（model/prompt/num_predict/num_gpu）で backend 差を評価する。',
  'ログにある確認事項のみを記載し、断定は再現証跡がある範囲に限定する。',
  '「公式サポート外」と「実行不可能」を同義に扱わない。',
  '失敗原因は GPU 世代全体ではなく、どの backend 経路で落ちるかに分解する。',
]);
ly += 4.9;

header(LX, ly, CW, '2', '調査で確定した事実', C.blue);
ly += 0.9;
panel(LX, ly, CW, 7.1);
bulletBox(LX + 0.18, ly + 0.18, CW - 0.36, 6.7, [
  'num_gpu は GPU 枚数ではなく GPU offload 層数（layers）を意味する。',
  'ROCm 側（:11435）では qwen3.5:2b + num_gpu=0,1,2,-1 を同一条件で完走。',
  'Vulkan 側（:11434）は num_gpu=0 のみ完走、1/2/-1 は HTTP 500。',
  'Vulkan 失敗は初期化失敗ではなく、load 後 computeBatch で SIGSEGV。',
  'ROCm 7.2 公式表で gfx900 非掲載でも、ローカル実体に gfx900 artifact 残存を確認。',
]);
ly += 7.5;

header(LX, ly, CW, '3', '結果テーブル（再現 run）', C.green);
ly += 0.9;
panel(LX, ly, CW, 7.8);

const rh = [
  { text: 'run_id', options: { fill: { color: C.green }, color: 'FFFFFF', bold: true, fontSize: 16 } },
  { text: 'backend', options: { fill: { color: C.green }, color: 'FFFFFF', bold: true, fontSize: 16 } },
  { text: '条件', options: { fill: { color: C.green }, color: 'FFFFFF', bold: true, fontSize: 16 } },
  { text: '結果', options: { fill: { color: C.green }, color: 'FFFFFF', bold: true, fontSize: 16 } },
];

const rb = [
  ['run_20260307_012643', 'ROCm', 'num_gpu=0,1,2,-1', 'all ok'],
  ['run_20260307_013050', 'Vulkan', 'num_gpu=0,1,2,-1', '0のみok'],
  ['run_20260307_011230', 'Vulkan', 'EPOCHS=3, num_gpu=0', '3/3 ok'],
  ['run_20260307_102504', 'Vulkan', '再検証 num_gpu=0', '3/3 ok'],
].map((row) => row.map((cell, i) => ({
  text: cell,
  options: {
    fontSize: 15,
    bold: i === 0,
    color: i === 3 && cell.includes('ok') ? C.green : C.txt,
  },
})));

s.addTable([rh, ...rb], {
  x: LX + 0.2,
  y: ly + 0.2,
  w: CW - 0.4,
  border: { pt: 1, color: C.line },
  colW: [(CW - 0.4) * 0.31, (CW - 0.4) * 0.16, (CW - 0.4) * 0.26, (CW - 0.4) * 0.27],
  rowH: [0.42, 0.6, 0.6, 0.6, 0.6],
});

s.addText('※ Vulkan は「常に失敗」ではなく、num_gpu=0 条件は安定。', {
  x: LX + 0.2,
  y: ly + 3.0,
  w: CW - 0.4,
  h: 0.5,
  fontFace: 'Calibri',
  fontSize: 17,
  color: C.dim,
  italic: true,
});

// Right column
header(RX, ry, CW, '4', 'ポスター旧版の不適切点（監査結果）', C.orange);
ry += 0.9;
panel(RX, ry, CW, 5.0);
bulletBox(RX + 0.18, ry + 0.18, CW - 0.36, 4.6, [
  '調査ログで裏付けていない外部研究の数値グラフを中核根拠としていた。',
  '「Vulkan compute path instability」の説明が、条件依存（num_gpu=0例外）を弱く表現していた。',
  '証跡にない強い一般化（legacy GPU全体への拡張解釈）が混在していた。',
  '出典境界が曖昧で、ローカル再現ログと背景情報が同一レイヤで提示されていた。',
]);
ry += 5.4;

header(RX, ry, CW, '5', '改訂方針（今回JS刷新）', C.orange);
ry += 0.9;
panel(RX, ry, CW, 4.6);
bulletBox(RX + 0.18, ry + 0.18, CW - 0.36, 4.2, [
  '主張を「このリポジトリの調査資料で追える内容」に限定。',
  '事実・解釈・未確定事項を分離して表記。',
  '再現 run_id を明示し、比較条件を固定して提示。',
  '外部研究紹介は削除（別スライド化すべき領域として分離）。',
]);
ry += 5.0;

header(RX, ry, CW, '6', '結論（現時点）', C.green);
ry += 0.9;
panel(RX, ry, CW, 6.4);
bulletBox(RX + 0.18, ry + 0.18, CW - 0.36, 6.0, [
  '同一条件比較の範囲では、Vega/gfx900 で ROCm/HIP は実行可能、Vulkan は offload 時に不安定。',
  'よって、今回の失敗を「Vega世代だから不可」と断定するのは不適切。',
  'ただし ROCm 7.2 公式保証外である事実は維持し、運用は暫定・条件付きとする。',
  '次フェーズ: Vulkan compute 経路のクラッシュ点をさらに局所化する。',
]);
ry += 6.8;

const fy = Math.max(ly + 8.3, ry + 0.3);
s.addShape(pres.shapes.RECTANGLE, {
  x: M,
  y: fy,
  w: W - (2 * M),
  h: 2.1,
  fill: { color: 'EEEEEE' },
  line: { color: C.line, pt: 1 },
});

s.addText('Reproducibility note', {
  x: M + 0.2,
  y: fy + 0.15,
  w: 4.2,
  h: 0.4,
  color: C.blue,
  bold: true,
  fontFace: 'Arial',
  fontSize: 18,
});

s.addText('ROCm: OLLAMA_HOST=http://127.0.0.1:11435 EPOCHS=1 NUM_PREDICT=512 NUM_GPU=0,1,2,-1 python vega-loop_qwen_rocm.py', {
  x: M + 0.2,
  y: fy + 0.58,
  w: W - (2 * M) - 0.4,
  h: 0.45,
  fontFace: 'Consolas',
  fontSize: 13,
  color: C.txt,
});

s.addText('Vulkan: OLLAMA_HOST=http://127.0.0.1:11434 EPOCHS=1 NUM_PREDICT=512 NUM_GPU=0,1,2,-1 python vega-loop_qwen_rocm.py', {
  x: M + 0.2,
  y: fy + 1.03,
  w: W - (2 * M) - 0.4,
  h: 0.45,
  fontFace: 'Consolas',
  fontSize: 13,
  color: C.txt,
});

s.addText('Unsupported ≠ Impossible / Evidence first, claim later.', {
  x: M,
  y: H - 0.52,
  w: W - (2 * M),
  h: 0.3,
  align: 'center',
  italic: true,
  color: C.dim,
  fontFace: 'Calibri',
  fontSize: 16,
});

pres.writeFile({ fileName: 'A0_Poster/2026-03-09/A0_Final_Poster_revised.pptx' })
  .then(() => console.log('DONE: revised poster generated'))
  .catch((e) => console.error(e));
