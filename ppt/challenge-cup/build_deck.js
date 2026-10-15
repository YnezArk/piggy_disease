// build_deck.js — 挑战杯风格幻灯片生成器（pptxgenjs）
// 风格：深蓝科技底 + 四栏胶囊标题 + 虚线框 + 白色卡片 + 蓝色流程按钮 + 底部渐变总结条
const PptxGenJS = require("pptxgenjs");
const pres = new PptxGenJS();

pres.defineLayout({ name: "W16x9", width: 13.333, height: 7.5 });
pres.layout = "W16x9";

const F = "微软雅黑";
const C = {
  bg: "071531",
  title: "FFFFFF",
  sub: "9FC0F0",
  navy: "0E2A57",
  navyDim: "44597C",
  blue: "1E6FE8",
  blueLt: "4FA3FF",
  cyan: "46CFFF",
  gold: "F5B93E",
  white: "FFFFFF",
  frame: "A9C9F2",
  cardText: "16355F",
  cardDim: "5A7196",
};
const M = 0.55;
const COLS = 4;
const GAP = 0.18;
const COLW = (13.333 - 2 * M - (COLS - 1) * GAP) / COLS; // ≈2.923
const FRAME_Y = 1.85;
const FRAME_H = 4.39;
const BG = { cover: "assets/bg_cover.jpg", content: "assets/bg_content.jpg" };

function shadow(o = 0.3, blur = 7, off = 2.2) {
  return { type: "outer", color: "000000", opacity: o, blur, offset: off, angle: 90 };
}
function tx(slide, text, o) {
  slide.addText(text, Object.assign({ fontFace: F, margin: 0, valign: "middle" }, o));
}
function bg(slide, which) {
  slide.background = { color: C.bg };
  slide.addImage({ path: BG[which], x: 0, y: 0, w: 13.333, h: 7.5 });
}
function colX(i) { return M + i * (COLW + GAP); }

// ── 页眉：大标题（左）+ 副标题（居中）────────────────────
function pageHead(slide, title, sub) {
  tx(slide, title, { x: M, y: 0.22, w: 4.6, h: 0.66, fontSize: 30, bold: true, color: C.title, charSpacing: 1.5 });
  tx(slide, sub, { x: M, y: 0.38, w: 13.333 - 2 * M, h: 0.42, fontSize: 14.5, color: C.sub, align: "center" });
}

// ── 栏目标题胶囊（图片渐变 + 白字）──────────────────────
function colHeader(slide, x, y, w, text) {
  const iw = 2.923;                       // 固定胶囊宽度，保持比例
  const ih = iw * 260 / 1260;
  const ix = x + w / 2 - iw / 2;
  slide.addImage({ path: "assets/pill.png", x: ix, y: y, w: iw, h: ih });
  const visY = y + ih * 30 / 260, visH = ih * 200 / 260;
  const visW = iw * 1200 / 1260, visX = ix + iw * 30 / 1260;
  tx(slide, text, { x: visX, y: visY, w: visW, h: visH, fontSize: 15, bold: true, color: C.white, align: "center" });
  return visY + visH;                     // 返回可见底边
}
function pillTop() { return 1.19 + 0.603 * 30 / 260; }

function dashedFrame(slide, x, y, w, h) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.07, line: { color: C.frame, width: 1, dashType: "dash", transparency: 35 } });
}

// ── 白色卡片 ─────────────────────────────────────────────
function card(slide, x, y, w, h, opts = {}) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: opts.r ?? 0.06, fill: { color: opts.fill ?? C.white }, line: { color: "FFFFFF", width: 0 }, shadow: shadow(opts.so ?? 0.32, 8, 2.5) });
}
function cardTitle(slide, x, y, w, text, color = C.blue) {
  slide.addShape("roundRect", { x, y: y + 0.10, w: 0.075, h: 0.20, rectRadius: 0.03, fill: { color } });
  tx(slide, text, { x: x + 0.18, y, w: w - 0.24, h: 0.40, fontSize: 11.5, bold: true, color: C.cardText });
}

// ── 流程按钮 + 箭头 ──────────────────────────────────────
function flowBtn(slide, x, y, w, text, h = 0.38, fs = 10.5) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.10, fill: { color: C.blue }, line: { color: "6FACFF", width: 0.75 }, shadow: shadow(0.3, 5, 1.6) });
  tx(slide, text, { x: x + 0.07, y, w: w - 0.14, h, fontSize: fs, bold: true, color: C.white, align: "center", lineSpacing: fs * 1.25 });
  return y + h;
}
function dArrow(slide, cx, y) {
  slide.addShape("downArrow", { x: cx - 0.085, y, w: 0.17, h: 0.155, fill: { color: "7FC4FF" }, line: { color: "7FC4FF", width: 0 } });
}
function rArrow(slide, x, y) {
  slide.addShape("rightArrow", { x, y, w: 0.165, h: 0.14, fill: { color: "7FC4FF" }, line: { color: "7FC4FF", width: 0 } });
}

// ── 白底小标签（chips）──────────────────────────────────
function chip(slide, x, y, w, h, text, opts = {}) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: h / 2, fill: { color: opts.fill ?? C.white }, line: opts.line ?? { color: "FFFFFF", width: 0 }, shadow: shadow(opts.so ?? 0.22, 5, 1.5) });
  tx(slide, text, { x: x + 0.05, y, w: w - 0.1, h, fontSize: opts.fs ?? 10.5, bold: true, color: opts.color ?? C.navy, align: "center" });
}

// ── 底部总结条 ───────────────────────────────────────────
function banner(slide, text) {
  const w = 13.333 - 2 * M, h = w * 230 / 2480;
  slide.addImage({ path: "assets/banner.png", x: M, y: 6.22, w, h });
  tx(slide, text, { x: M + 0.45, y: 6.22 + h * 40 / 230, w: w - 0.9, h: h * 150 / 230, fontSize: 18.5, bold: true, color: C.white, align: "center", charSpacing: 1 });
}

// ── 大数字统计 ───────────────────────────────────────────
function stat(slide, x, y, w, value, label, color = C.blue, label2) {
  tx(slide, value, { x, y, w, h: 0.42, fontSize: 23, bold: true, color, align: "center" });
  tx(slide, label, { x, y: y + 0.40, w, h: 0.26, fontSize: 9, color: C.cardDim, align: "center" });
  if (label2) tx(slide, label2, { x, y: y + 0.62, w, h: 0.22, fontSize: 8.2, color: "8A9CB8", align: "center" });
}

// ── 迷你柱状图（白卡内）─────────────────────────────────
function barChart(slide, x, y, w, h, items) {
  const max = Math.max(...items.map(d => d.v));
  const n = items.length, bW = Math.min(0.26, (w - 0.3 - (n - 1) * 0.10) / n), g = (w - n * bW) / (n + 1);
  const baseY = y + h - 0.30, maxH = h - 0.62;
  items.forEach((d, i) => {
    const bx = x + g + i * (bW + g);
    const bh = Math.max(0.05, d.v / max * maxH);
    slide.addShape("roundRect", { x: bx, y: baseY - bh, w: bW, h: bh, rectRadius: 0.035, fill: { color: d.hl ? C.gold : "4E9BF5" }, line: { color: d.hl ? C.gold : "4E9BF5", width: 0 } });
    tx(slide, String(d.v), { x: bx - 0.09, y: baseY - bh - 0.22, w: bW + 0.18, h: 0.20, fontSize: 8.5, bold: true, color: C.cardText, align: "center" });
    tx(slide, d.l, { x: bx - 0.14, y: baseY + 0.03, w: bW + 0.28, h: 0.22, fontSize: 8.5, color: C.cardDim, align: "center" });
  });
}

// ── 迷你波形（白卡内）───────────────────────────────────
function waveBars(slide, x, y, w, h, color = "4E9BF5") {
  const hs = [0.22, 0.4, 0.6, 0.35, 0.8, 0.5, 0.95, 0.42, 0.7, 0.3, 0.55, 0.4, 0.25];
  const bW = 0.055, g = (w - 0.2 - hs.length * bW) / (hs.length - 1);
  const baseY = y + h;
  hs.forEach((v, i) => {
    const bx = x + 0.1 + i * (bW + g);
    const bh = Math.max(0.05, v * (h - 0.08));
    slide.addShape("roundRect", { x: bx, y: baseY - bh, w: bW, h: bh, rectRadius: 0.025, fill: { color: i % 4 === 2 ? C.cyan : color }, line: { width: 0 } });
  });
}

// ── 迷你节点图（白卡内：圆点 + 连线 + 虚线高亮）──────────
function miniGraph(slide, x, y, w, h) {
  const pts = [
    [0.16, 0.72], [0.30, 0.30], [0.46, 0.62], [0.60, 0.24], [0.76, 0.52], [0.88, 0.30],
  ].map(([px, py]) => [x + px * w, y + py * h]);
  const links = [[0, 1], [1, 2], [2, 3], [2, 4], [4, 5], [0, 2]];
  links.forEach(([a, b]) => {
    const [x1, y1] = pts[a], [x2, y2] = pts[b];
    slide.addShape("line", { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), flipH: x2 < x1, flipV: y2 < y1, line: { color: "9CC0EC", width: 1.2 } });
  });
  pts.forEach(([px, py], i) => {
    const gold = i === 3;
    slide.addShape("ellipse", { x: px - 0.055, y: py - 0.055, w: 0.11, h: 0.11, fill: { color: gold ? C.gold : "2E7BE8" }, line: { color: "FFFFFF", width: 1 } });
    if (gold) slide.addShape("ellipse", { x: px - 0.115, y: py - 0.115, w: 0.23, h: 0.23, line: { color: "E8A22B", width: 1.2, dashType: "dash" } });
  });
}

// ── 清单行（白卡内）──────────────────────────────────────
function checkRow(slide, x, y, w, text, dotColor = C.blue) {
  slide.addShape("roundRect", { x, y: y + 0.045, w: 0.09, h: 0.09, rectRadius: 0.02, fill: { color: dotColor } });
  tx(slide, text, { x: x + 0.17, y: y - 0.07, w: w - 0.17, h: 0.34, fontSize: 9.5, color: C.cardText, lineSpacing: 12 });
}

// ── 图片占位框（可删掉后粘贴截图）────────────────────────
function placeholder(slide, x, y, w, h, title, sub) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.08, fill: { color: "FFFFFF", transparency: 93 }, line: { color: "7FB2EF", width: 1.3, dashType: "dash" } });
  const c = C.gold, t = 0.035, L = 0.30;
  [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]].forEach(([px, py, sx, sy]) => {
    slide.addShape("rect", { x: sx > 0 ? px : px - L, y: sy > 0 ? py : py - t, w: L, h: t, fill: { color: c }, line: { width: 0 } });
    slide.addShape("rect", { x: sx > 0 ? px : px - t, y: sy > 0 ? py : py - L, w: t, h: L, fill: { color: c }, line: { width: 0 } });
  });
  const cx0 = x + w / 2, cy0 = y + h / 2 - 0.42;
  slide.addShape("ellipse", { x: cx0 - 0.17, y: cy0 - 0.17, w: 0.34, h: 0.34, line: { color: "7FB2EF", width: 1.2 }, fill: { color: "FFFFFF", transparency: 88 } });
  slide.addShape("rect", { x: cx0 - 0.085, y: cy0 - 0.012, w: 0.17, h: 0.024, fill: { color: "9CCBFF" }, line: { width: 0 } });
  slide.addShape("rect", { x: cx0 - 0.012, y: cy0 - 0.085, w: 0.024, h: 0.17, fill: { color: "9CCBFF" }, line: { width: 0 } });
  tx(slide, title, { x: x + 0.2, y: cy0 + 0.26, w: w - 0.4, h: 0.32, fontSize: 12.5, bold: true, color: "D5E6FF", align: "center" });
  tx(slide, sub, { x: x + 0.3, y: cy0 + 0.58, w: w - 0.6, h: 0.5, fontSize: 9.3, color: "8FB4E8", align: "center", lineSpacing: 12.5 });
}
// 卡片正文行
function lines(slide, x, y, w, h, arr, fs = 10, color = C.cardText, ls) {
  tx(slide, arr.map((t, i) => ({ text: t, options: { breakLine: i < arr.length - 1 } })), { x, y, w, h, fontSize: fs, color, lineSpacing: ls ?? fs * 1.55 });
}

/* ═══════════════════════ 板块封面 ═══════════════════════ */
{
  const s = pres.addSlide();
  bg(s, "cover");
  chip(s, 0.9, 1.52, 3.60, 0.42, "猪咳嗽智能诊疗系统 · 板块四", { fs: 11.5 });
  tx(s, "诊疗决策板块", { x: 0.86, y: 2.16, w: 10.5, h: 1.10, fontSize: 48, bold: true, color: C.white, charSpacing: 2 });
  tx(s, "声学辨病 × 中兽医辨证论治 —— 两层认知模型 + 知识底座", { x: 0.9, y: 3.36, w: 11.0, h: 0.46, fontSize: 18, bold: true, color: "CFE2FF" });
  tx(s, "检测 → 诊断 → 组方 → 反馈，构成可溯源的诊疗闭环", { x: 0.9, y: 3.86, w: 11.0, h: 0.40, fontSize: 14, color: "A9C6F5" });
  const feats = ["声学特征 · 84 维", "SSLRB 集成辨病", "RAG 辨证组方", "用药安全护栏"];
  feats.forEach((t, i) => chip(s, 0.9 + i * 2.72, 4.78, 2.52, 0.5, t, { fs: 12 }));
}

/* ═══════════════════════ 系统架构 ═══════════════════════ */
{
  const s = pres.addSlide();
  bg(s, "content");
  pageHead(s, "系统架构", "两层认知模型 · 检测 → 诊断 → 组方 → 反馈 闭环");
  const heads = ["监测输入", "辨病层", "论治层", "校核与闭环"];
  heads.forEach((t, i) => { colHeader(s, colX(i), 1.19, COLW, t); dashedFrame(s, colX(i), FRAME_Y, COLW, FRAME_H); });
  const cx = i => colX(i) + 0.14, cw = COLW - 0.28;

  // Col1 监测输入
  card(s, cx(0), 2.02, cw, 1.18);
  waveBars(s, cx(0) + 0.14, 2.20, cw - 0.28, 0.62);
  tx(s, "咳嗽声片段（16 kHz）", { x: cx(0) + 0.16, y: 2.86, w: cw - 0.32, h: 0.26, fontSize: 8.8, color: C.cardDim });
  ["猪只档案 · 体重月龄", "体温 · 精神状态", "猪舍环境 · 氨气温湿度"].forEach((t, i) => chip(s, cx(0), 3.40 + i * 0.52, cw, 0.42, t, { fs: 9.8 }));
  card(s, cx(0), 5.10, cw, 0.95, { so: 0.22 });
  lines(s, cx(0) + 0.16, 5.26, cw - 0.32, 0.7, ["多模态特征输入", "（体温/行为/环境 · 预留接口）"], 9.3, C.cardDim, 13.5);

  // Col2 辨病层
  card(s, cx(1), 2.02, cw, 1.42);
  miniGraph(s, cx(1) + 0.18, 2.10, cw - 0.36, 1.02);
  tx(s, "声学特征空间 · 疾病判别（6 类）", { x: cx(1) + 0.16, y: 3.14, w: cw - 0.32, h: 0.24, fontSize: 8.8, color: C.cardDim, align: "center" });
  let y2 = 3.62;
  ["84 维特征提取", "SSLRB 集成分类", "疾病 + 置信度"].forEach((t, i, arr) => {
    y2 = flowBtn(s, cx(1), y2, cw, t, 0.44, 10);
    if (i < arr.length - 1) { dArrow(s, cx(1) + cw / 2, y2 + 0.05); y2 += 0.26; }
  });

  // Col3 论治层
  let y3 = 2.05;
  ["RAG 三库检索", "辨证 Agent · 证型/治则", "组方 Agent · 方剂/剂量"].forEach((t, i, arr) => {
    y3 = flowBtn(s, cx(2), y3, cw, t, 0.62, 10.5);
    if (i < arr.length - 1) { dArrow(s, cx(2) + cw / 2, y3 + 0.07); y3 += 0.32; }
  });
  card(s, cx(2), 4.62, cw, 1.30, { so: 0.22 });
  lines(s, cx(2) + 0.16, 4.76, cw - 0.32, 1.05, ["知识底座：", "辨证库 · 论治库 · 典籍库", "检索必有出处，杜绝虚构"], 9.3, C.cardDim, 13.5);

  // Col4 校核与闭环
  card(s, cx(3), 2.02, cw, 1.62);
  cardTitle(s, cx(3) + 0.16, 2.14, cw - 0.32, "规则校验（不依赖 LLM）");
  checkRow(s, cx(3) + 0.18, 2.62, cw - 0.36, "十八反 · 十九畏 —— 硬拦截");
  checkRow(s, cx(3) + 0.18, 2.98, cw - 0.36, "幻觉剂量 8 倍上限 —— 硬拦截");
  checkRow(s, cx(3) + 0.18, 3.34, cw - 0.36, "孕猪慎用 —— 软警示", C.gold);
  let y4 = 4.02;
  ["结果落库（可追溯）", "疗效反馈（闭环）"].forEach((t, i, arr) => {
    y4 = flowBtn(s, cx(3), y4, cw, t, 0.5, 10);
    if (i < arr.length - 1) { dArrow(s, cx(3) + cw / 2, y4 + 0.06); y4 += 0.3; }
  });
  card(s, cx(3), 5.42, cw, 0.62, { so: 0.22 });
  lines(s, cx(3) + 0.14, 5.52, cw - 0.28, 0.44, ["处方记录 + 校验报告同步入库"], 9, C.cardDim, 12);

  // 跨栏箭头
  [3.72, 3.72, 4.16].forEach((ay, i) => rArrow(s, colX(i) + COLW + 0.008, ay));

  banner(s, "辨病定疾病 · 论治定方案 —— 两层认知模型 + 知识底座，构建可溯源的中兽医诊疗闭环");
}

/* ═══════════════════════ 辨病模块 ═══════════════════════ */
{
  const s = pres.addSlide();
  bg(s, "content");
  pageHead(s, "辨病模块", "咳嗽声学特征 + SSLRB 集成学习 · 六类疾病识别");
  const heads = ["数据底座", "特征工程", "模型路线", "评测结果"];
  heads.forEach((t, i) => { colHeader(s, colX(i), 1.19, COLW, t); dashedFrame(s, colX(i), FRAME_Y, COLW, FRAME_H); });
  const cx = i => colX(i) + 0.14, cw = COLW - 0.28;

  // Col1 数据
  card(s, cx(0), 2.05, cw, 2.65);
  cardTitle(s, cx(0) + 0.16, 2.17, cw - 0.32, "540 条标注样本 · 六类");
  barChart(s, cx(0) + 0.22, 2.68, cw - 0.44, 1.55, [
    { l: "正常", v: 167 }, { l: "流感", v: 135 }, { l: "支原体", v: 148 },
    { l: "蓝耳", v: 28, hl: true }, { l: "胸膜", v: 49, hl: true }, { l: "其他", v: 13, hl: true },
  ]);
  tx(s, "黄标类别样本稀缺 —— 小样本 + 强不平衡是本模块最大挑战", { x: cx(0) + 0.16, y: 4.32, w: cw - 0.32, h: 0.30, fontSize: 8.8, color: C.cardDim, lineSpacing: 11 });
  card(s, cx(0), 4.90, cw, 0.96, { so: 0.22 });
  lines(s, cx(0) + 0.16, 5.04, cw - 0.32, 0.70, ["8 : 1 : 1 分层划分 · 固定随机种子", "增强样本不入库 —— 防止污染特征表"], 8.8, C.cardDim, 12.5);

  // Col2 特征
  card(s, cx(1), 2.05, cw, 2.65);
  cardTitle(s, cx(1) + 0.16, 2.17, cw - 0.32, "84 维声学特征向量");
  [["MFCC 13 维", "梅尔倒谱系数"], ["logFBank 64 维", "对数梅尔频谱"], ["时域 3 维", "能量 · 过零率 · RMS"], ["频域 4 维", "质心 · 带宽 · 平坦度 · 滚降"]].forEach((row, i) => {
    const ry = 2.72 + i * 0.44;
    chip(s, cx(1) + 0.16, ry, 1.06, 0.36, row[0], { fs: 8.6 });
    tx(s, row[1], { x: cx(1) + 1.30, y: ry, w: cw - 1.46, h: 0.36, fontSize: 8.8, color: C.cardDim });
  });
  tx(s, "均值池化拼接 · 16 kHz · 1.0 s · n_fft 2048", { x: cx(1) + 0.16, y: 4.50, w: cw - 0.32, h: 0.26, fontSize: 8.8, color: C.cardDim });
  card(s, cx(1), 4.90, cw, 0.96, { so: 0.22 });
  lines(s, cx(1) + 0.16, 5.04, cw - 0.32, 0.70, ["与库内特征复算误差 < 1e-13", "全链路可复现 · 另设 142 维扩展口径"], 8.8, C.cardDim, 12.5);

  // Col3 模型
  let y3 = 2.15;
  ["SVM-Stacking · 3 基分类器", "LR-Bagging · 3 元学习器", "ROS 随机上采样"].forEach((t, i, arr) => {
    y3 = flowBtn(s, cx(2), y3, cw, t, i < 2 ? 0.58 : 0.46, i < 2 ? 10.5 : 10);
    if (i < arr.length - 1) { dArrow(s, cx(2) + cw / 2, y3 + 0.06); y3 += 0.30; }
  });
  card(s, cx(2), 4.55, cw, 1.32, { so: 0.22 });
  lines(s, cx(2) + 0.16, 4.70, cw - 0.32, 1.05, ["架构来源：纪楠(2023)", "γ 三档基分类器 + ROS 上采样", "适配重度不平衡场景"], 9, C.cardDim, 13.5);

  // Col4 结果
  card(s, cx(3), 2.05, cw, 2.65);
  cardTitle(s, cx(3) + 0.16, 2.17, cw - 0.32, "独立测试集评估");
  stat(s, cx(3) + 0.14, 2.66, cw / 2 - 0.20, "0.75+", "Macro-F1", C.blue, "（主指标）");
  stat(s, cx(3) + cw / 2 + 0.02, 2.66, cw / 2 - 0.22, "0.833", "测试准确率");
  stat(s, cx(3) + 0.14, 3.58, cw / 2 - 0.20, "0.941", "健康类召回");
  stat(s, cx(3) + cw / 2 + 0.02, 3.58, cw / 2 - 0.22, "95.4%", "全样本回测");
  tx(s, "5 折分层 CV + 固定划分双协议验证", { x: cx(3) + 0.16, y: 4.38, w: cw - 0.32, h: 0.24, fontSize: 8.8, color: C.cardDim, align: "center" });
  card(s, cx(3), 4.90, cw, 0.96, { so: 0.22 });
  lines(s, cx(3) + 0.16, 5.06, cw - 0.32, 0.66, ["不平衡下准确率易虚高", "以 Macro-F1 为主判据衡量病类识别"], 8.8, C.cardDim, 12.5);

  banner(s, "小样本、强不平衡条件下达标 —— 病类识别 Macro-F1 ≥ 0.75，健康猪“零漏报”优先");
}

/* ═══════════════════════ 论治模块 ═══════════════════════ */
{
  const s = pres.addSlide();
  bg(s, "content");
  pageHead(s, "论治模块", "RAG 知识检索 + LLM 两阶段辨证组方 · 规则护栏");
  const heads = ["知识底座", "辨证 Agent", "组方 Agent", "校验 Agent"];
  heads.forEach((t, i) => { colHeader(s, colX(i), 1.19, COLW, t); dashedFrame(s, colX(i), FRAME_Y, COLW, FRAME_H); });
  const cx = i => colX(i) + 0.14, cw = COLW - 0.28;

  // Col1 知识底座
  [["辨证库", "11 条多维体征规则", "体温 · 咳喘 · 排泄物 → 证候"], ["论治库", "14 首方剂 · 含剂量加减", "证候 → 基础方 + 化裁规则"], ["典籍库", "230 段典籍语料", "治则依据 · 全带出处"]].forEach((row, i) => {
    const ry = 2.05 + i * 1.06;
    card(s, cx(0), ry, cw, 0.94);
    tx(s, row[0], { x: cx(0) + 0.16, y: ry + 0.10, w: cw - 0.32, h: 0.30, fontSize: 11.5, bold: true, color: C.blue });
    tx(s, row[1], { x: cx(0) + 0.16, y: ry + 0.40, w: cw - 0.32, h: 0.26, fontSize: 9.3, bold: true, color: C.cardText });
    tx(s, row[2], { x: cx(0) + 0.16, y: ry + 0.64, w: cw - 0.32, h: 0.24, fontSize: 8.5, color: C.cardDim });
  });
  ["理", "法", "方", "药"].forEach((t, i) => chip(s, cx(0) + 0.05 + i * 0.66, 5.32, 0.56, 0.44, t, { fs: 13, color: C.blue }));
  tx(s, "理 · 法 · 方 · 药 逻辑链", { x: cx(0), y: 5.86, w: cw, h: 0.26, fontSize: 8.8, color: C.cardDim, align: "center" });

  // Col2 辨证
  let y2 = 2.06;
  ["查询改写（口语 → 标准词）", "双路检索（语义 + SQL 精确）", "辨证推理（证型 · 治则）"].forEach((t, i, arr) => {
    y2 = flowBtn(s, cx(1), y2, cw, t, 0.60, 9.6);
    if (i < arr.length - 1) { dArrow(s, cx(1) + cw / 2, y2 + 0.07); y2 += 0.31; }
  });
  card(s, cx(1), 4.60, cw, 1.32, { so: 0.22 });
  cardTitle(s, cx(1) + 0.16, 4.72, cw - 0.32, "辨病纠错 · 交叉验证", C.gold);
  lines(s, cx(1) + 0.16, 5.14, cw - 0.32, 0.70, ["症状与辨病矛盾时", "双重验证指出冲突，按症状辨证"], 9, C.cardDim, 13);

  // Col3 组方
  let y3 = 2.06;
  ["基础方匹配（论治库）", "随症加减化裁", "剂量换算 ×体重 ×病情"].forEach((t, i, arr) => {
    y3 = flowBtn(s, cx(2), y3, cw, t, 0.60, 9.8);
    if (i < arr.length - 1) { dArrow(s, cx(2) + cw / 2, y3 + 0.07); y3 += 0.31; }
  });
  card(s, cx(2), 4.60, cw, 1.32, { so: 0.22 });
  cardTitle(s, cx(2) + 0.16, 4.72, cw - 0.32, "组方有据可查");
  lines(s, cx(2) + 0.16, 5.14, cw - 0.32, 0.70, ["方剂、剂量、禁忌", "全部源自知识库，引用真实文献"], 9, C.cardDim, 13);

  // Col4 校验
  card(s, cx(3), 2.06, cw, 1.72);
  cardTitle(s, cx(3) + 0.16, 2.18, cw - 0.32, "安全护栏 · 确定性规则");
  checkRow(s, cx(3) + 0.18, 2.66, cw - 0.36, "剂量区间核对（药材库）");
  checkRow(s, cx(3) + 0.18, 3.02, cw - 0.36, "十八反 · 十九畏 配伍禁忌");
  checkRow(s, cx(3) + 0.18, 3.38, cw - 0.36, "拦截结果写入处方记录", C.gold);
  card(s, cx(3), 4.06, cw, 1.30, { so: 0.22 });
  stat(s, cx(3) + 0.14, 4.24, cw - 0.28, "40 / 40", "自动化测试全绿");
  lines(s, cx(3) + 0.16, 4.92, cw - 0.32, 0.34, ["校验不依赖 LLM —— 安全必须确定性"], 8.8, C.cardDim, 12);

  // 跨栏箭头
  [3.52, 3.52, 3.30].forEach((ay, i) => rArrow(s, colX(i) + COLW + 0.008, ay));

  banner(s, "让大模型只做推理、不做拍板 —— 检索有依据，组方有出处，用药有护栏");
}

/* ═══════════════════════ 系统演示（截图位）═══════════════════════ */
{
  const s = pres.addSlide();
  bg(s, "content");
  pageHead(s, "系统演示", "关键链路运行界面 · 图片位可替换为实拍截图");
  const w2 = (13.333 - 2 * M - 0.35) / 2, h2 = (FRAME_H - 0.30) / 2;
  const px = i => M + i * (w2 + 0.35), py = j => FRAME_Y + j * (h2 + 0.30);
  placeholder(s, px(0), py(0), w2, h2, "辨病推理 · 终端输出", "predict.py 单条 wav → 疾病 / 置信度 / Top3 概率分布");
  placeholder(s, px(1), py(0), w2, h2, "辨病评估 · 混淆矩阵", "5 折分层 CV 报告 / 全样本回测结果图");
  placeholder(s, px(0), py(1), w2, h2, "论治链路 · 交互终端", "interactive_demo.py 辨证 · 组方 · 校验全过程输出");
  placeholder(s, px(1), py(1), w2, h2, "API 服务 · 接口文档", "/docs 页面 或 POST /api/diagnose-audio 返回 JSON");
  banner(s, "全链路可运行、可复现 —— 从上传音频到输出处方，端到端一次完成");
}

/* ═══════════════════════ 成果与展望 ═══════════════════════ */
{
  const s = pres.addSlide();
  bg(s, "content");
  pageHead(s, "成果与展望", "从“听见咳嗽”到“开对药方”");
  const w3 = (13.333 - 2 * M - 2 * GAP) / 3;
  const c3x = i => M + i * (w3 + GAP);
  const heads = ["已建成", "应用价值", "下一步"];
  heads.forEach((t, i) => { colHeader(s, c3x(i), 1.19, w3, t); dashedFrame(s, c3x(i), FRAME_Y, w3, FRAME_H); });

  const items = [
    ["辨病 + 论治全链路 API 贯通", "上传咳嗽音频 → 输出诊疗方案", "40 项自动化测试全绿", "论证案例 A–F 全部通过（含辨病纠错）", "六类辨病模型达标（Macro-F1 ≥ 0.75）"],
    ["咳嗽早筛 —— 疫情预警从“事后”到“事前”", "精准减抗 —— 辨证论治替代盲目用药", "中兽医临床经验数字化、可传承", "契合国家“减抗替抗”与智慧养殖方向"],
    ["样本扩容 + 迁移学习（目标 Macro-F1 0.85）", "疗效反馈闭环 · 处方库持续自学习", "多模态融合（体温 · 行为 · 环境）", "对接小程序与猪场管理系统"],
  ];
  items.forEach((arr, i) => {
    card(s, c3x(i) + 0.14, 2.05, w3 - 0.28, 3.55);
    const step = arr.length >= 5 ? 0.64 : 0.80;
    arr.forEach((t, j) => {
      const ry = 2.32 + j * step;
      slideDot(s, c3x(i) + 0.34, ry + 0.06, i);
      tx(s, t, { x: c3x(i) + 0.56, y: ry - 0.06, w: w3 - 0.85, h: 0.56, fontSize: 10.5, color: C.cardText, lineSpacing: 14 });
    });
  });

  banner(s, "让 AI 成为猪场里的“中兽医助手” —— 早发现、辨得准、开得对");
}
function slideDot(s, x, y, i) {
  const col = [C.blue, C.cyan, C.gold][i % 3];
  s.addShape("roundRect", { x, y, w: 0.11, h: 0.11, rectRadius: 0.025, fill: { color: col }, line: { width: 0 } });
}

/* ── 输出 ── */
pres.writeFile({ fileName: "猪咳嗽智能诊疗-挑战杯.pptx" }).then(f => console.log("DONE ->", f));
