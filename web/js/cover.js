/* Sefer cover designer: fill in the details, pick a template, get a beautiful print-ready cover (front or full wrap) */
const GOLD = ["#7a5a14", "#f6dc8b", "#b8892b", "#fff1b8", "#8f6a1c"], SILVER = ["#6b6f78", "#f4f6fa", "#a9afba", "#ffffff", "#7c818c"];
const COVER_TEMPLATES = {
  blank: { name: "Blank (design your own)", bg: "#f6f1e6", metal: ["#1e3a5f", "#1e3a5f", "#1e3a5f", "#1e3a5f", "#1e3a5f"], frame: "none", corner: "none", texture: "none", ornament: "none", ink: true },
  leather: { name: "Leather & Gold", bg: "#4a2a17", metal: GOLD, frame: "double", corner: "flourish", texture: "leather", ornament: "star" },
  navy: { name: "Navy Gilt", bg: "#14284a", metal: GOLD, frame: "diamonds", corner: "flourish", texture: "cloth", ornament: "crown" },
  burgundy: { name: "Burgundy Ornate", bg: "#5e1222", metal: GOLD, frame: "panel", corner: "flourish", texture: "leather", ornament: "crown" },
  parchment: { name: "Parchment", bg: "#efe2c2", metal: ["#3b2a17", "#5b4229", "#3b2a17", "#6b4e2e", "#3b2a17"], frame: "thin", corner: "dots", texture: "parchment", ornament: "line", ink: true },
  emerald: { name: "Emerald Arch", bg: "#0f3b2e", metal: GOLD, frame: "arch", corner: "none", texture: "cloth", ornament: "pomegranate" },
  minimal: { name: "Modern Minimal", bg: "#f7f5f0", metal: ["#1e3a5f", "#1e3a5f", "#1e3a5f", "#1e3a5f", "#1e3a5f"], frame: "none", corner: "none", texture: "none", ornament: "bar", ink: true },
  black: { name: "Black & Silver", bg: "#111214", metal: SILVER, frame: "double", corner: "flourish", texture: "leather", ornament: "star" },
  marble: { name: "White Marble", bg: "#f2f0ec", metal: GOLD, frame: "double", corner: "dots", texture: "marble", ornament: "rosette" },
  marbleBlack: { name: "Black Marble", bg: "#1a1a1d", metal: GOLD, frame: "thin", corner: "flourish", texture: "marble", ornament: "star" },
  vilna: { name: "Vilna Title Page", bg: "#f1e6cc", metal: ["#2b1d10","#4a3520","#2b1d10","#5a4128","#2b1d10"], frame: "gate", corner: "none", texture: "parchment", ornament: "none", ink: true },
  deco: { name: "Art Deco", bg: "#0e3b43", metal: GOLD, frame: "deco", corner: "none", texture: "none", ornament: "fan" },
  wreath: { name: "Laurel Wreath", bg: "#3d0f1c", metal: GOLD, frame: "wreath", corner: "none", texture: "leather", ornament: "none" },
  scroll: { name: "Torah Scroll", bg: "#2a1a0f", metal: GOLD, frame: "scroll", corner: "none", texture: "wood", ornament: "crown" },
  night: { name: "Starry Night", bg: "#0b1530", bg2: "#2c3e7a", metal: ["#9a7a2c","#fff4c2","#e1c06a","#fffbe6","#b8892b"], frame: "none", corner: "none", texture: "stars", ornament: "menorah" },
  jerusalem: { name: "Jerusalem Stone", bg: "#d9c7a0", metal: ["#4a3418","#6b4e2a","#4a3418","#7a5a32","#4a3418"], frame: "thin", corner: "none", texture: "stone", ornament: "skyline", ink: true },
  moroccan: { name: "Geometric Star", bg: "#1d3557", metal: GOLD, frame: "double", corner: "none", texture: "geo", ornament: "star" },
  watercolor: { name: "Watercolor", bg: "#fbf8f2", metal: ["#29425e","#29425e","#29425e","#29425e","#29425e"], frame: "none", corner: "none", texture: "watercolor", ornament: "line", ink: true },
  split: { name: "Modern Split", bg: "#f4efe6", bg2: "#1e3a5f", metal: ["#1e3a5f","#1e3a5f","#1e3a5f","#1e3a5f","#1e3a5f"], frame: "split", corner: "none", texture: "none", ornament: "none", ink: true },
  medallion: { name: "Olive Medallion", bg: "#3b4a23", metal: GOLD, frame: "medallion", corner: "flourish", texture: "cloth", ornament: "none" },
  wood: { name: "Olive Wood", bg: "#7a5230", metal: ["#2a170a","#4a2c15","#2a170a","#5a3a1c","#2a170a"], frame: "thin", corner: "dots", texture: "wood", ornament: "luchos", ink: true },
  luchos: { name: "Royal Tablets", bg: "#1b2a6b", metal: SILVER, frame: "double", corner: "flourish", texture: "cloth", ornament: "luchos" },
  ketubah: { name: "Rose Arch", bg: "#f6e8e6", metal: ["#7a2e3a","#b3505f","#7a2e3a","#c66b78","#7a2e3a"], frame: "ketubah", corner: "none", texture: "parchment", ornament: "none", ink: true },
  linen: { name: "Grey Linen", bg: "#8d9096", metal: ["#ffffff","#ffffff","#ffffff","#ffffff","#ffffff"], frame: "none", corner: "none", texture: "cloth", ornament: "rosette" },
  sunrise: { name: "Golden Sunrise", bg: "#f7c873", bg2: "#d1495b", metal: ["#3a1020","#3a1020","#3a1020","#3a1020","#3a1020"], frame: "none", corner: "none", texture: "gradient", ornament: "sun", ink: true },
  forest: { name: "Forest Green Gilt", bg: "#123524", metal: GOLD, frame: "lattice", corner: "none", texture: "leather", ornament: "pomegranate" },
  sky: { name: "Pomegranate Blue", bg: "#dbe8f3", metal: ["#7a5a14", "#d9a940", "#a87b1f", "#e9c66b", "#7a5a14"], frame: "diamonds", corner: "dots", texture: "parchment", ornament: "pomegranate", ink: true },
};
const SIZES = { "6 × 9 in": [6, 9], "5.5 × 8.5 in": [5.5, 8.5], "7 × 10 in": [7, 10], "8.5 × 11 in": [8.5, 11], "A5": [5.83, 8.27], "A4": [8.27, 11.69], "Square 8 in": [8, 8] };
const Cover = {
  d: null,
  defaults() {
    return { id: null, tpl: "leather", top: "בס״ד", title: "שערי תורה", subtitle: "חידושים וביאורים על התורה", author: "מאת הרב פלוני אלמוני", author2: "", publisher: "ירושלים", year: "", dedication: "",
      back: "ספר זה נכתב לזכות…", spine: "", size: "6 × 9 in", wrap: false, titleFont: "Frank Ruhl Libre", bodyFont: "David Libre", bg: "", metal: "", emboss: true, texture: 70, titleSize: 100,
      hideText: false, layers: [], bgImage: null, bgOpacity: 100 };
  },
  render(el) {
    const fonts = App.fontList();
    const fsel = id => `<select id="${id}">${fonts.map(f => `<option>${esc(f)}</option>`).join("")}</select>`;
    el.innerHTML = `<div class="cover-wrap"><div class="cover-form">
      <h1 class="page-title">📕 Sefer cover</h1>
      <div class="tpl-grid" id="cvTpls"></div>
      <label>Top line</label><input id="cv_top" class="he-input">
      <label>Title</label><input id="cv_title" class="he-input">
      <label>Subtitle</label><input id="cv_subtitle" class="he-input">
      <label>Author</label><input id="cv_author" class="he-input">
      <label>Second author line</label><input id="cv_author2" class="he-input">
      <label>Place / publisher</label><input id="cv_publisher" class="he-input">
      <label>Year (blank = this Hebrew year)</label><input id="cv_year" class="he-input">
      <label>Dedication (small, bottom)</label><input id="cv_dedication" class="he-input">
      <label>Back cover text (full wrap)</label><textarea id="cv_back" class="he-input"></textarea>
      <div class="row"><label style="flex:1">Size<select id="cv_size">${Object.keys(SIZES).map(s => `<option>${s}</option>`).join("")}</select></label><label style="margin-top:22px"><input type="checkbox" id="cv_wrap"> Full wrap (back + spine)</label></div>
      <label>Title font</label>${fsel("cv_titleFont")}<label>Text font</label>${fsel("cv_bodyFont")}
      <div class="row"><label>Cover colour <input type="color" id="cv_bg"></label><label>Lettering <input type="color" id="cv_metal"></label><label><input type="checkbox" id="cv_emboss"> Emboss</label></div>
      <label>Texture <input type="range" id="cv_texture" min="0" max="100"></label><label>Title size <input type="range" id="cv_titleSize" min="50" max="160"></label>
      <h2 style="margin-top:16px">✏️ My own design</h2>
      <p class="small muted" style="margin:0">Add your own text, pictures, ornaments and shapes. Drag them on the cover; arrows nudge, Delete removes.</p>
      <div class="row" style="margin-top:6px"><button class="btn small" id="cvAddText">+ Text</button><button class="btn small" id="cvAddImg">+ Picture</button>
        <select id="cvAddOrn" class="small"><option value="">+ Ornament…</option>${["star", "crown", "menorah", "luchos", "pomegranate", "rosette", "fan", "flourish", "diamond"].map(o => `<option>${o}</option>`).join("")}</select>
        <select id="cvAddShape" class="small"><option value="">+ Shape…</option><option>rect</option><option>ellipse</option><option>line</option></select></div>
      <div class="row" style="margin-top:6px"><button class="btn small" id="cvBgImg">🖼 Background picture</button><button class="btn small" id="cvBgNo">✕ remove</button>
        <label class="small">opacity <input type="range" id="cv_bgOpacity" min="10" max="100" style="width:80px"></label></div>
      <label style="margin-top:6px"><input type="checkbox" id="cv_hideText" style="width:auto"> Hide the built-in texts (use only my own)</label>
      <div id="cvLayers" style="margin-top:6px"></div><div id="cvProps"></div>
      <div class="row" style="margin-top:12px"><button class="btn primary" id="cvSave">💾 Save</button><button class="btn" id="cvNew">New</button><button class="btn" id="cvOpen">Open…</button></div>
      <div class="row" style="margin-top:6px"><button class="btn gold" id="cvPng">⤓ PNG (300 dpi)</button><button class="btn" id="cvPdf">🖨 Print / PDF</button></div>
      </div><div class="cover-stage"><canvas id="cvCan"></canvas></div></div>`;
    this.d = this.defaults();
    this.fill();
    $$(".cover-form input, .cover-form select, .cover-form textarea", el).forEach(i => i.addEventListener("input", () => { this.read(); this.draw(); }));
    $("#cvSave", el).onclick = () => this.save();
    $("#cvNew", el).onclick = () => { this.d = this.defaults(); this.fill(); this.draw(); };
    $("#cvOpen", el).onclick = () => { App.show("mylib"); Personal.tab("covers"); };
    $("#cvPng", el).onclick = () => this.exportPng();
    $("#cvPdf", el).onclick = () => this.print();
    this.drawThumbs();
    this.initDesign(el);
    document.fonts.ready.then(() => this.draw());
    this.draw();
  },
  fill() {
    const d = this.d, T = COVER_TEMPLATES[d.tpl];
    for (const k of Object.keys(d)) { const i = $("#cv_" + k); if (!i) continue; if (i.type === "checkbox") i.checked = !!d[k]; else if (i.type === "color") { if (d[k]) i.value = d[k]; } else i.value = d[k] ?? ""; }
    if (!d.bg) $("#cv_bg").value = T.bg; if (!d.metal) $("#cv_metal").value = T.metal[2];
    if (![...$("#cv_titleFont").options].some(o => o.value === d.titleFont)) $("#cv_titleFont").selectedIndex = 0;
    $$("#cvTpls canvas").forEach(c => c.classList.toggle("sel", c.dataset.t === d.tpl));
  },
  read() {
    for (const k of Object.keys(this.d)) { const i = $("#cv_" + k); if (!i) continue; this.d[k] = i.type === "checkbox" ? i.checked : (i.type === "range" ? +i.value : i.value); }
  },
  drawThumbs() {
    const g = $("#cvTpls"); g.innerHTML = "";
    for (const [k, T] of Object.entries(COVER_TEMPLATES)) {
      const c = document.createElement("canvas"); c.width = 120; c.height = 170; c.dataset.t = k; c.title = T.name;
      g.appendChild(c); this.paint(c.getContext("2d"), 120, 170, { ...this.d, layers: [], bgImage: null, hideText: false, tpl: k, bg: "", metal: "", title: "ספר", subtitle: "", author: "", author2: "", top: "", publisher: "", dedication: "", year: " " }, 0.14);
      c.onclick = () => { this.d.tpl = k; this.d.bg = ""; this.d.metal = ""; this.fill(); this.read(); this.d.bg = ""; this.d.metal = ""; this.draw(); };
    }
  },
  dims(scale) { const [w, h] = SIZES[this.d.size] || [6, 9]; const dpi = 100 * scale; const spine = this.d.wrap ? 0.9 : 0; return { W: Math.round((this.d.wrap ? 2 * w + spine : w) * dpi), H: Math.round(h * dpi), front: Math.round(w * dpi), spine: Math.round(spine * dpi) }; },
  async draw() {
    this._screen = true;
    const c = $("#cvCan"); if (!c) return;
    if (!this.d.year && this._year === undefined) { this._year = ""; try { const r = await App.api("tool_run", { id: "year_convert", args: { n: new Date().getFullYear() } }); this._year = (r.result.match(/\(([^/]+)\//) || [])[1] || ""; } catch (e) { } }
    const { W, H } = this.dims(1); c.width = W; c.height = H;
    this.paintFull(c.getContext("2d"), 1);
  },
  paintFull(ctx, scale) {
    const { W, H, front, spine } = this.dims(scale);
    if (!this.d.wrap) return this.paint(ctx, W, H, this.d, scale);
    // back | spine | front
    ctx.save(); this.paint(ctx, front, H, { ...this.d, title: "", subtitle: "", author: "", author2: "", top: "", publisher: "", dedication: "", year: " ", back: this.d.back, isBack: true }, scale); ctx.restore();
    ctx.save(); ctx.translate(front, 0); this.background(ctx, spine, H, COVER_TEMPLATES[this.d.tpl], this.d, scale);
    const m = this.metal(ctx, 0, 0, spine, H); ctx.strokeStyle = m; ctx.lineWidth = 2 * scale; for (const y of [H * .08, H * .92]) { ctx.beginPath(); ctx.moveTo(spine * .12, y); ctx.lineTo(spine * .88, y); ctx.stroke(); }
    ctx.translate(spine / 2, H / 2); ctx.rotate(Math.PI / 2); ctx.direction = "rtl"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = `700 ${spine * .42}px "${this.d.titleFont}", serif`; ctx.fillStyle = m; ctx.fillText(this.d.spine || this.d.title, 0, 0);
    ctx.font = `${spine * .25}px "${this.d.bodyFont}", serif`; ctx.fillText((this.d.author || "").replace(/^מאת\s*/, ""), H * .32, 0);
    ctx.restore();
    ctx.save(); ctx.translate(front + spine, 0); this.paint(ctx, front, H, this.d, scale); ctx.restore();
  },
  rng(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; },
  metal(ctx, x, y, w, h, colors) {
    const col = colors || (this.d.metal ? [this.shade(this.d.metal, -45), this.shade(this.d.metal, 60), this.d.metal, this.shade(this.d.metal, 75), this.shade(this.d.metal, -30)] : COVER_TEMPLATES[this.d.tpl].metal);
    const g = ctx.createLinearGradient(x, y, x + w, y + h); col.forEach((c, i) => g.addColorStop(i / (col.length - 1), c)); return g;
  },
  shade(hex, p) { const n = parseInt(hex.slice(1), 16); const f = c => Math.max(0, Math.min(255, Math.round(c + (p > 0 ? (255 - c) : c) * p / 100))); return "#" + [f(n >> 16), f((n >> 8) & 255), f(n & 255)].map(v => v.toString(16).padStart(2, "0")).join(""); },
  background(ctx, W, H, T, d, scale) {
    const bg = d.bg || T.bg; ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
    const amt = (d.texture ?? 70) / 100, r = this.rng(12345);
    if (T.texture === "leather" && amt) {
      for (let i = 0; i < W * H / 60 * amt; i++) { const x = r() * W, y = r() * H, s = r() * 2.2 * scale + .4; ctx.fillStyle = r() > .5 ? `rgba(255,255,255,${.035 * amt})` : `rgba(0,0,0,${.09 * amt})`; ctx.fillRect(x, y, s, s); }
      for (let i = 0; i < 60 * amt; i++) { ctx.strokeStyle = `rgba(0,0,0,${.06 * amt})`; ctx.lineWidth = r() * 1.5 * scale; ctx.beginPath(); const x = r() * W, y = r() * H; ctx.moveTo(x, y); ctx.bezierCurveTo(x + r() * 60 * scale, y + r() * 20 * scale, x + r() * 80 * scale, y - r() * 30 * scale, x + r() * 120 * scale, y + r() * 10 * scale); ctx.stroke(); }
    }
    if (T.texture === "cloth" && amt) { ctx.globalAlpha = .07 * amt; ctx.strokeStyle = "#fff"; ctx.lineWidth = .6 * scale; for (let x = 0; x < W; x += 3 * scale) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); } ctx.strokeStyle = "#000"; for (let y = 0; y < H; y += 3 * scale) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); } ctx.globalAlpha = 1; }
    if (T.texture === "parchment" && amt) { for (let i = 0; i < 26 * amt; i++) { const x = r() * W, y = r() * H, rad = (40 + r() * 140) * scale; const g = ctx.createRadialGradient(x, y, 0, x, y, rad); g.addColorStop(0, `rgba(150,110,50,${.10 * amt})`); g.addColorStop(1, "rgba(150,110,50,0)"); ctx.fillStyle = g; ctx.fillRect(x - rad, y - rad, 2 * rad, 2 * rad); } }
    if (T.texture === "marble") {
      const dark = this.lum(bg) < .4;
      for (let i = 0; i < 14; i++) {
        ctx.strokeStyle = dark ? `rgba(220,220,230,${(.05 + r() * .12) * amt})` : `rgba(90,90,110,${(.06 + r() * .14) * amt})`;
        ctx.lineWidth = (0.6 + r() * 2.2) * scale; ctx.beginPath(); let x = r() * W, y = -20, dx = (r() - .3) * 3;
        ctx.moveTo(x, y); while (y < H + 20) { x += dx * 10 * scale + (r() - .5) * 26 * scale; y += 14 * scale; ctx.lineTo(x, y); } ctx.stroke();
      }
      for (let i = 0; i < 30; i++) { const x = r() * W, y = r() * H, rad = (30 + r() * 120) * scale; const g = ctx.createRadialGradient(x, y, 0, x, y, rad); g.addColorStop(0, dark ? `rgba(255,255,255,${.04 * amt})` : `rgba(120,120,140,${.05 * amt})`); g.addColorStop(1, "rgba(0,0,0,0)"); ctx.fillStyle = g; ctx.fillRect(x - rad, y - rad, 2 * rad, 2 * rad); }
    }
    if (T.texture === "wood") {
      for (let y = 0; y < H; y += 2 * scale) { const n = Math.sin(y / (17 * scale)) * .5 + Math.sin(y / (5.3 * scale) + r()) * .5; ctx.fillStyle = `rgba(0,0,0,${(.04 + .06 * Math.abs(n)) * amt})`; ctx.fillRect(0, y, W, 1.2 * scale); }
      for (let i = 0; i < 4; i++) { const x = r() * W, y = r() * H; ctx.strokeStyle = `rgba(40,20,5,${.18 * amt})`; ctx.lineWidth = 1.2 * scale; for (let k = 1; k < 7; k++) { ctx.beginPath(); ctx.ellipse(x, y, k * 9 * scale, k * 4 * scale, 0, 0, 7); ctx.stroke(); } }
    }
    if (T.texture === "stone") {
      const bh = 70 * scale, bw = 140 * scale;
      for (let y = 0, row = 0; y < H; y += bh, row++) for (let x = -(row % 2) * bw / 2; x < W; x += bw) {
        ctx.fillStyle = `rgba(${r() > .5 ? "255,255,255" : "90,60,20"},${(.04 + r() * .07) * amt})`; ctx.fillRect(x + 2 * scale, y + 2 * scale, bw - 4 * scale, bh - 4 * scale);
        ctx.strokeStyle = `rgba(80,60,30,${.25 * amt})`; ctx.lineWidth = 1.5 * scale; ctx.strokeRect(x, y, bw, bh);
      }
      for (let i = 0; i < W * H / 80 * amt; i++) { ctx.fillStyle = `rgba(70,50,20,${.08 * amt})`; ctx.fillRect(r() * W, r() * H, 1.3 * scale, 1.3 * scale); }
    }
    if (T.texture === "stars" || T.texture === "gradient") {
      const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, bg); g.addColorStop(1, d.bg2 || T.bg2 || bg); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      if (T.texture === "stars") for (let i = 0; i < 260 * amt; i++) { const x = r() * W, y = r() * H * .85, s2 = r() * 1.8 * scale + .3; ctx.fillStyle = `rgba(255,250,230,${.3 + r() * .7})`; ctx.beginPath(); ctx.arc(x, y, s2, 0, 7); ctx.fill(); }
    }
    if (T.texture === "geo" && amt) {
      ctx.save(); ctx.strokeStyle = this.metal(ctx, 0, 0, W, H); ctx.globalAlpha = .16 * amt; ctx.lineWidth = 1.2 * scale; const st = 54 * scale;
      for (let y = 0; y < H + st; y += st) for (let x = 0; x < W + st; x += st) this.star8(ctx, x, y, st * .45); ctx.restore();
    }
    if (T.texture === "watercolor") {
      const cols = ["#7fb3d5", "#f5b7b1", "#a9dfbf", "#f9e79f", "#d2b4de"];
      for (let i = 0; i < 18; i++) { const x = r() * W, y = r() * H, rad = (80 + r() * 220) * scale; const g = ctx.createRadialGradient(x, y, 0, x, y, rad); const c = cols[i % cols.length]; g.addColorStop(0, c + "55"); g.addColorStop(.7, c + "22"); g.addColorStop(1, c + "00"); ctx.fillStyle = g; ctx.fillRect(x - rad, y - rad, 2 * rad, 2 * rad); }
    }
    const v = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * .25, W / 2, H / 2, Math.max(W, H) * .75);
    v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, `rgba(0,0,0,${T.ink ? .12 : .45})`); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  },
  paint(ctx, W, H, d, scale) {
    const T = COVER_TEMPLATES[d.tpl]; const s = W / 600;
    this.background(ctx, W, H, T, d, scale);
    if (!d.isBack) this.paintBgImage(ctx, W, H, d);
    const m = this.metal(ctx, 0, 0, W, H);
    ctx.strokeStyle = m; ctx.fillStyle = m;
    const M = 34 * s;
    // frames
    if (T.frame === "double" || T.frame === "panel" || T.frame === "diamonds") { ctx.lineWidth = 5 * s; ctx.strokeRect(M, M, W - 2 * M, H - 2 * M); ctx.lineWidth = 1.6 * s; ctx.strokeRect(M + 12 * s, M + 12 * s, W - 2 * M - 24 * s, H - 2 * M - 24 * s); }
    if (T.frame === "thin") { ctx.lineWidth = 1.5 * s; ctx.strokeRect(M, M, W - 2 * M, H - 2 * M); ctx.strokeRect(M + 6 * s, M + 6 * s, W - 2 * M - 12 * s, H - 2 * M - 12 * s); }
    if (T.frame === "panel") { ctx.lineWidth = 2.5 * s; const px = W * .16, py = H * .2; this.roundRect(ctx, px, py, W - 2 * px, H * .42, 18 * s); ctx.stroke(); }
    if (T.frame === "diamonds") { const step = 22 * s; for (let x = M + 30 * s; x < W - M - 20 * s; x += step) { this.diamond(ctx, x, M + 6 * s, 4 * s); this.diamond(ctx, x, H - M - 6 * s, 4 * s); } for (let y = M + 30 * s; y < H - M - 20 * s; y += step) { this.diamond(ctx, M + 6 * s, y, 4 * s); this.diamond(ctx, W - M - 6 * s, y, 4 * s); } }
    if (T.frame === "arch") this.arch(ctx, W, H, s);
    if (T.frame === "gate") this.gate(ctx, W, H, s);
    if (T.frame === "deco") this.deco(ctx, W, H, s);
    if (T.frame === "wreath") this.wreath(ctx, W / 2, H * .38, W * .36, s);
    if (T.frame === "scroll") this.scrollFrame(ctx, W, H, s);
    if (T.frame === "split") { ctx.save(); ctx.fillStyle = d.bg2 || T.bg2; ctx.fillRect(0, H * .58, W, H * .42); ctx.fillStyle = this.metal(ctx, 0, 0, W, H); ctx.fillRect(W * .12, H * .58 - 6 * s, W * .3, 12 * s); ctx.restore(); }
    if (T.frame === "medallion") { ctx.lineWidth = 4 * s; ctx.beginPath(); ctx.ellipse(W / 2, H * .4, W * .34, H * .27, 0, 0, 7); ctx.stroke(); ctx.lineWidth = 1.4 * s; ctx.beginPath(); ctx.ellipse(W / 2, H * .4, W * .34 - 12 * s, H * .27 - 12 * s, 0, 0, 7); ctx.stroke(); for (let i = 0; i < 36; i++) { const a = i * Math.PI / 18; this.diamond(ctx, W / 2 + (W * .34 + 14 * s) * Math.cos(a), H * .4 + (H * .27 + 14 * s) * Math.sin(a), 3.5 * s); } ctx.lineWidth = 3 * s; ctx.strokeRect(M, M, W - 2 * M, H - 2 * M); }
    if (T.frame === "lattice") { ctx.lineWidth = 3 * s; ctx.strokeRect(M, M, W - 2 * M, H - 2 * M); const st = 16 * s; ctx.lineWidth = 1.2 * s; for (const [x0, y0, x1, y1] of [[M, M, W - M, M], [M, H - M, W - M, H - M]]) for (let x = x0; x < x1 - st; x += st) { ctx.beginPath(); ctx.moveTo(x, y0 - 7 * s); ctx.lineTo(x + st, y0 + 7 * s); ctx.moveTo(x, y0 + 7 * s); ctx.lineTo(x + st, y0 - 7 * s); ctx.stroke(); } for (const x0 of [M, W - M]) for (let y = M; y < H - M - st; y += st) { ctx.beginPath(); ctx.moveTo(x0 - 7 * s, y); ctx.lineTo(x0 + 7 * s, y + st); ctx.moveTo(x0 + 7 * s, y); ctx.lineTo(x0 - 7 * s, y + st); ctx.stroke(); } }
    if (T.frame === "ketubah") { const l = W * .13, rr = W * .87, top = H * .18, base = H * .9; ctx.lineWidth = 3 * s; ctx.beginPath(); ctx.moveTo(l, base); ctx.lineTo(l, top + H * .1); ctx.quadraticCurveTo(l, top, W / 2, top - H * .06); ctx.quadraticCurveTo(rr, top, rr, top + H * .1); ctx.lineTo(rr, base); ctx.closePath(); ctx.stroke(); for (let y = top + H * .12; y < base; y += 22 * s) { ctx.beginPath(); ctx.arc(l - 12 * s, y, 3 * s, 0, 7); ctx.arc(rr + 12 * s, y, 3 * s, 0, 7); ctx.fill(); } this.rosette(ctx, W / 2, top - H * .02, 16 * s); }
    if (T.corner === "flourish") for (const [x, y, sx, sy] of [[M, M, 1, 1], [W - M, M, -1, 1], [M, H - M, 1, -1], [W - M, H - M, -1, -1]]) this.flourish(ctx, x, y, sx, sy, s);
    if (T.corner === "dots") for (const [x, y] of [[M, M], [W - M, M], [M, H - M], [W - M, H - M]]) { ctx.beginPath(); ctx.arc(x, y, 6 * s, 0, 7); ctx.fill(); }
    if (d.isBack) { this.textBlock(ctx, d.back || "", W / 2, H * .3, W * .66, `${24 * s}px "${d.bodyFont}", serif`, 1.6, d); return; }
    // ornaments
    const oy = H * .17;
    if (T.ornament === "star") this.star(ctx, W / 2, oy, 26 * s);
    if (T.ornament === "crown") this.crown(ctx, W / 2, oy, 34 * s);
    if (T.ornament === "pomegranate") { this.pomegranate(ctx, W / 2, oy, 26 * s); this.pomegranate(ctx, W / 2 - 60 * s, oy + 10 * s, 15 * s); this.pomegranate(ctx, W / 2 + 60 * s, oy + 10 * s, 15 * s); }
    if (T.ornament === "menorah") this.menorah(ctx, W / 2, oy, 34 * s);
    if (T.ornament === "luchos") this.luchosDraw(ctx, W / 2, oy, 30 * s);
    if (T.ornament === "rosette") this.rosette(ctx, W / 2, oy, 26 * s);
    if (T.ornament === "fan") this.fan(ctx, W / 2, oy + 22 * s, 46 * s);
    if (T.ornament === "sun") { ctx.save(); ctx.globalAlpha = .9; ctx.beginPath(); ctx.arc(W / 2, H * .9, W * .32, Math.PI, 0); ctx.fillStyle = "rgba(255,255,255,.35)"; ctx.fill(); for (let i = 0; i < 13; i++) { const a = Math.PI + i * Math.PI / 12; ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.lineWidth = 3 * s; ctx.beginPath(); ctx.moveTo(W / 2 + W * .36 * Math.cos(a), H * .9 + W * .36 * Math.sin(a)); ctx.lineTo(W / 2 + W * .5 * Math.cos(a), H * .9 + W * .5 * Math.sin(a)); ctx.stroke(); } ctx.restore(); }
    if (T.ornament === "skyline") this.skyline(ctx, W, H, s);
    if (T.ornament === "line") { ctx.lineWidth = 1.5 * s; ctx.beginPath(); ctx.moveTo(W * .3, oy); ctx.lineTo(W * .7, oy); ctx.stroke(); this.diamond(ctx, W / 2, oy, 7 * s); }
    if (T.ornament === "bar") { ctx.fillRect(W * .12, H * .12, 70 * s, 8 * s); }
    // text
    const align = T.ornament === "bar" ? "right" : "center", ax = align === "right" ? W * .88 : W / 2;
    const txt = (t, y, font, size, opts = {}) => {
      if (!t || d.hideText) return; ctx.save(); ctx.direction = "rtl"; ctx.textAlign = align; ctx.textBaseline = "middle";
      let fs = size; ctx.font = `${opts.bold ? "700 " : ""}${fs}px "${font}", "Frank Ruhl Libre", "David", serif`;
      while (ctx.measureText(t).width > W * .76 && fs > 8) { fs -= 2; ctx.font = `${opts.bold ? "700 " : ""}${fs}px "${font}", "Frank Ruhl Libre", "David", serif`; }
      const g = this.metal(ctx, ax - W * .3, y - fs, W * .6, fs * 2);
      if (d.emboss && !T.ink) { ctx.fillStyle = "rgba(0,0,0,.55)"; ctx.fillText(t, ax + 1.5 * s, y + 2 * s); ctx.fillStyle = "rgba(255,255,255,.18)"; ctx.fillText(t, ax - 1 * s, y - 1 * s); }
      ctx.fillStyle = g; ctx.fillText(t, ax, y); ctx.restore();
    };
    txt(d.top, M + 38 * s, d.bodyFont, 18 * s);
    const ts = 74 * s * (d.titleSize || 100) / 100;
    const titleY = { panel: H * .34, arch: H * .42, gate: H * .4, wreath: H * .36, medallion: H * .36, split: H * .3, scroll: H * .38, ketubah: H * .4 }[T.frame] || H * .36;
    const lines = (d.title || "").split(/\n|\s{2,}/);
    lines.forEach((l, i) => txt(l, titleY + (i - (lines.length - 1) / 2) * ts * 1.15, d.titleFont, ts, { bold: true }));
    txt(d.subtitle, titleY + ts * (lines.length / 2 + .55) + 16 * s, d.bodyFont, 28 * s);
    if (T.ornament !== "bar" && !d.hideText) { ctx.save(); ctx.strokeStyle = m; ctx.lineWidth = 1.2 * s; const ly = titleY + ts * (lines.length / 2 + .55) + 52 * s; ctx.beginPath(); ctx.moveTo(W * .38, ly); ctx.lineTo(W * .62, ly); ctx.stroke(); this.diamond(ctx, W / 2, ly, 4 * s); ctx.restore(); }
    const L = { split: [.68, .86], medallion: [.74, .86], gate: [.66, .76], deco: [.6, .86], wreath: [.66, .86] }[T.frame] || [.64, null];
    if (T.ornament === "skyline") L[1] = .72;
    const onBand = y => T.frame === "split" && y > H * .58;
    const txt2 = (t, y, font, size) => { if (onBand(y)) { const keep = this.d.metal; this.d.metal = "#ffffff"; txt(t, y, font, size); this.d.metal = keep; } else txt(t, y, font, size); };
    txt2(d.author, H * L[0], d.bodyFont, 30 * s);
    txt2(d.author2, H * L[0] + 40 * s, d.bodyFont, 22 * s);
    txt2([d.publisher, d.year === " " ? "" : (d.year || this._year || "")].filter(Boolean).join(" · "), L[1] ? H * L[1] : H - M - 64 * s, d.bodyFont, 22 * s);
    txt2(d.dedication, H - M - 30 * s, d.bodyFont, 14 * s);
    this.paintLayers(ctx, W, H, d, s);
  },
  textBlock(ctx, text, x, y, w, font, lh, d) {
    ctx.save(); ctx.font = font; ctx.direction = "rtl"; ctx.textAlign = "center"; ctx.fillStyle = this.metal(ctx, 0, 0, w, 300);
    const size = parseFloat(font); let line = "", yy = y;
    for (const word of text.split(/\s+/)) { const t = line ? line + " " + word : word; if (ctx.measureText(t).width > w) { ctx.fillText(line, x, yy); yy += size * lh; line = word; } else line = t; }
    ctx.fillText(line, x, yy); ctx.restore();
  },
  lum(hex) { const n = parseInt((hex || "#000000").slice(1), 16); return ((n >> 16) * .299 + ((n >> 8) & 255) * .587 + (n & 255) * .114) / 255; },
  star8(ctx, x, y, r) { ctx.beginPath(); for (let i = 0; i < 16; i++) { const a = i * Math.PI / 8, rr = i % 2 ? r * .55 : r; ctx[i ? "lineTo" : "moveTo"](x + rr * Math.cos(a), y + rr * Math.sin(a)); } ctx.closePath(); ctx.stroke(); },
  rosette(ctx, x, y, r) { ctx.save(); ctx.lineWidth = r * .08; for (let i = 0; i < 8; i++) { ctx.beginPath(); ctx.ellipse(x + r * .5 * Math.cos(i * Math.PI / 4), y + r * .5 * Math.sin(i * Math.PI / 4), r * .5, r * .2, i * Math.PI / 4, 0, 7); ctx.stroke(); } ctx.beginPath(); ctx.arc(x, y, r * .18, 0, 7); ctx.fill(); ctx.restore(); },
  menorah(ctx, x, y, r) {
    ctx.save(); ctx.lineWidth = r * .09; ctx.lineCap = "round"; const top = y - r * .55, base = y + r * .45;
    for (let i = 1; i <= 3; i++) { ctx.beginPath(); ctx.arc(x, top, r * i * .3, 0, Math.PI); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, base); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - r * .35, base + r * .12); ctx.lineTo(x + r * .35, base + r * .12); ctx.stroke();
    for (let i = -3; i <= 3; i++) { ctx.beginPath(); ctx.ellipse(x + i * r * .3, top - r * .17, r * .06, r * .13, 0, 0, 7); ctx.fill(); }
    ctx.restore(); },
  luchosDraw(ctx, x, y, r) { ctx.save(); ctx.lineWidth = r * .08; for (const dx of [-.52, .52]) { const cx = x + dx * r; ctx.beginPath(); ctx.moveTo(cx - r * .45, y + r * .8); ctx.lineTo(cx - r * .45, y - r * .3); ctx.arc(cx, y - r * .3, r * .45, Math.PI, 0); ctx.lineTo(cx + r * .45, y + r * .8); ctx.closePath(); ctx.stroke(); for (let k = 0; k < 5; k++) { ctx.beginPath(); ctx.moveTo(cx - r * .28, y - r * .25 + k * r * .22); ctx.lineTo(cx + r * .28, y - r * .25 + k * r * .22); ctx.stroke(); } } ctx.restore(); },
  fan(ctx, x, y, r) { ctx.save(); ctx.lineWidth = r * .05; for (let i = 0; i <= 8; i++) { const a = Math.PI + i * Math.PI / 8; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + r * Math.cos(a), y + r * Math.sin(a)); ctx.stroke(); } for (const k of [.45, .75, 1]) { ctx.beginPath(); ctx.arc(x, y, r * k, Math.PI, 0); ctx.stroke(); } ctx.restore(); },
  skyline(ctx, W, H, s) { ctx.save(); ctx.globalAlpha = .85; const b = H * .9; ctx.beginPath(); ctx.moveTo(W * .1, b); const pts = [[.1, .86], [.18, .86], [.18, .82], [.24, .82], [.24, .86], [.32, .86], [.32, .8], [.34, .78], [.36, .8], [.36, .86], [.42, .86]]; pts.forEach(([a, c]) => ctx.lineTo(W * a, H * c)); ctx.lineTo(W * .42, H * .84); ctx.arc(W * .5, H * .84, W * .08, Math.PI, 0); ctx.lineTo(W * .58, H * .86); [[.64, .86], [.64, .81], [.67, .81], [.67, .77], [.69, .77], [.69, .81], [.72, .81], [.72, .86], [.82, .86], [.82, .83], [.9, .83], [.9, b]].forEach(([a, c]) => ctx.lineTo(W * a, H * c)); ctx.closePath(); ctx.fill(); ctx.restore(); },
  gate(ctx, W, H, s) {
    const l = W * .1, r = W * .9, top = H * .16, base = H * .86, cw = W * .09;
    ctx.lineWidth = 2 * s;
    for (const x of [l, r - cw]) { ctx.strokeRect(x, top + H * .08, cw, base - top - H * .08); for (let y = top + H * .1; y < base - 10 * s; y += 18 * s) { ctx.beginPath(); ctx.moveTo(x + cw * .3, y); ctx.lineTo(x + cw * .3, y + 12 * s); ctx.moveTo(x + cw * .7, y); ctx.lineTo(x + cw * .7, y + 12 * s); ctx.stroke(); } ctx.fillRect(x - 8 * s, base, cw + 16 * s, 12 * s); ctx.fillRect(x - 8 * s, top + H * .08 - 12 * s, cw + 16 * s, 12 * s); }
    ctx.lineWidth = 3 * s; ctx.beginPath(); ctx.moveTo(l, top + H * .08 - 12 * s); ctx.lineTo(r, top + H * .08 - 12 * s); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(l - 10 * s, top + H * .06); ctx.lineTo(W / 2, top - H * .04); ctx.lineTo(r + 10 * s, top + H * .06); ctx.stroke();
    ctx.beginPath(); ctx.arc(W / 2, top + H * .1, (r - l - 2 * cw) / 2 - 6 * s, Math.PI, 0); ctx.stroke();
    for (let i = 0; i < 4; i++) ctx.fillRect(l - 16 * s - i * 6 * s, base + 12 * s + i * 8 * s, r - l + 32 * s + i * 12 * s, 3 * s);
  },
  deco(ctx, W, H, s) {
    const M = 30 * s; ctx.lineWidth = 2 * s; ctx.strokeRect(M, M, W - 2 * M, H - 2 * M);
    for (let k = 1; k <= 3; k++) { ctx.beginPath(); ctx.moveTo(W * .5 - k * 30 * s, M); ctx.lineTo(W * .5 - k * 30 * s, M + k * 26 * s); ctx.lineTo(W * .5 + k * 30 * s, M + k * 26 * s); ctx.lineTo(W * .5 + k * 30 * s, M); ctx.stroke(); }
    for (const [cx, cy, a0] of [[M, M, 0], [W - M, M, Math.PI / 2], [W - M, H - M, Math.PI], [M, H - M, -Math.PI / 2]]) for (let k = 1; k <= 4; k++) { ctx.beginPath(); ctx.arc(cx, cy, k * 22 * s, a0, a0 + Math.PI / 2); ctx.stroke(); }
    for (let y = H * .7; y < H * .74; y += 6 * s) { ctx.beginPath(); ctx.moveTo(W * .2, y); ctx.lineTo(W * .8, y); ctx.stroke(); }
  },
  wreath(ctx, cx, cy, R, s) {
    ctx.save(); ctx.lineWidth = 2.5 * s;
    for (const side of [-1, 1]) { ctx.beginPath(); ctx.arc(cx, cy, R, side < 0 ? Math.PI * .55 : Math.PI * .45, side < 0 ? Math.PI * 1.45 : -Math.PI * .45, side > 0); ctx.stroke();
      for (let i = 0; i < 12; i++) { const a = Math.PI / 2 + side * (.12 + i * .23); const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a); for (const o of [-1, 1]) { ctx.save(); ctx.translate(x, y); ctx.rotate(a + o * .7 + (side < 0 ? Math.PI : 0)); ctx.beginPath(); ctx.ellipse(0, -9 * s, 4 * s, 10 * s, 0, 0, 7); ctx.fill(); ctx.restore(); } } }
    ctx.restore();
  },
  scrollFrame(ctx, W, H, s) {
    const l = W * .12, r = W * .88, t = H * .12, b = H * .82;
    ctx.save(); ctx.fillStyle = "#f3e7c9"; ctx.fillRect(l, t, r - l, b - t); ctx.restore();
    ctx.lineWidth = 2 * s; ctx.strokeRect(l, t, r - l, b - t);
    for (const y of [t, b]) { this.roundRect(ctx, l - 26 * s, y - 14 * s, r - l + 52 * s, 28 * s, 14 * s); ctx.fill(); for (const x of [l - 26 * s, r + 26 * s]) { ctx.beginPath(); ctx.arc(x, y, 18 * s, 0, 7); ctx.fill(); } }
    for (const x of [l - 26 * s, r + 26 * s]) { ctx.fillRect(x - 4 * s, t - 60 * s, 8 * s, 46 * s); ctx.fillRect(x - 4 * s, b + 14 * s, 8 * s, 46 * s); }
  },
  roundRect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); },
  diamond(ctx, x, y, r) { ctx.beginPath(); ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath(); ctx.fill(); },
  star(ctx, x, y, r) { ctx.save(); ctx.lineWidth = r * .14; for (const rot of [0, Math.PI]) { ctx.beginPath(); for (let i = 0; i < 3; i++) { const a = rot + i * 2 * Math.PI / 3 - Math.PI / 2; ctx[i ? "lineTo" : "moveTo"](x + r * Math.cos(a), y + r * Math.sin(a)); } ctx.closePath(); ctx.stroke(); } ctx.restore(); },
  crown(ctx, x, y, r) { ctx.beginPath(); ctx.moveTo(x - r, y + r * .5); ctx.lineTo(x - r, y - r * .2); ctx.lineTo(x - r * .5, y + r * .15); ctx.lineTo(x, y - r * .55); ctx.lineTo(x + r * .5, y + r * .15); ctx.lineTo(x + r, y - r * .2); ctx.lineTo(x + r, y + r * .5); ctx.closePath(); ctx.fill(); for (const dx of [-1, 0, 1]) { ctx.beginPath(); ctx.arc(x + dx * r * (dx ? 1 : 0), y - r * (dx ? .32 : .68), r * .12, 0, 7); ctx.fill(); } ctx.fillRect(x - r, y + r * .58, 2 * r, r * .14); },
  pomegranate(ctx, x, y, r) { ctx.beginPath(); ctx.arc(x, y + r * .15, r * .78, 0, 7); ctx.fill(); ctx.beginPath(); ctx.moveTo(x - r * .3, y - r * .5); for (let i = 0; i < 5; i++) { ctx.lineTo(x - r * .3 + i * r * .15, y - r * (i % 2 ? .62 : .95)); } ctx.lineTo(x + r * .3, y - r * .5); ctx.closePath(); ctx.fill(); },
  flourish(ctx, x, y, sx, sy, s) {
    ctx.save(); ctx.translate(x, y); ctx.scale(sx, sy); ctx.lineWidth = 2.2 * s; ctx.beginPath();
    ctx.moveTo(14 * s, 14 * s); ctx.bezierCurveTo(60 * s, 10 * s, 80 * s, 40 * s, 52 * s, 52 * s); ctx.bezierCurveTo(30 * s, 60 * s, 30 * s, 34 * s, 44 * s, 34 * s);
    ctx.moveTo(14 * s, 14 * s); ctx.bezierCurveTo(10 * s, 60 * s, 40 * s, 80 * s, 52 * s, 52 * s);
    ctx.moveTo(14 * s, 14 * s); ctx.lineTo(90 * s, 14 * s); ctx.moveTo(14 * s, 14 * s); ctx.lineTo(14 * s, 90 * s); ctx.stroke();
    ctx.beginPath(); ctx.arc(14 * s, 14 * s, 5 * s, 0, 7); ctx.fill(); ctx.restore();
  },
  arch(ctx, W, H, s) {
    const l = W * .14, r = W * .86, top = H * .3, base = H * .86, cx = W / 2, rad = (r - l) / 2;
    ctx.lineWidth = 4 * s; ctx.beginPath(); ctx.moveTo(l, base); ctx.lineTo(l, top); ctx.arc(cx, top, rad, Math.PI, 0); ctx.lineTo(r, base); ctx.stroke();
    ctx.lineWidth = 1.5 * s; ctx.beginPath(); ctx.moveTo(l + 12 * s, base); ctx.lineTo(l + 12 * s, top); ctx.arc(cx, top, rad - 12 * s, Math.PI, 0); ctx.lineTo(r - 12 * s, base); ctx.stroke();
    for (const x of [l - 14 * s, r + 2 * s]) { ctx.fillRect(x, top, 12 * s, base - top); ctx.fillRect(x - 6 * s, base, 24 * s, 10 * s); ctx.fillRect(x - 6 * s, top - 10 * s, 24 * s, 10 * s); }
    ctx.fillRect(l - 20 * s, base + 10 * s, r - l + 40 * s, 6 * s);
  },
  /* ===================== free design ===================== */
  img(src) {
    this._imgs = this._imgs || {};
    if (!this._imgs[src]) { const im = new Image(); im.onload = () => this.draw(); im.src = src; this._imgs[src] = im; }
    const im = this._imgs[src]; return im.complete && im.naturalWidth ? im : null;
  },
  paintBgImage(ctx, W, H, d) {
    if (!d.bgImage) return; const im = this.img(d.bgImage); if (!im) return;
    const r = Math.max(W / im.naturalWidth, H / im.naturalHeight), w = im.naturalWidth * r, h = im.naturalHeight * r;
    ctx.save(); ctx.globalAlpha = (d.bgOpacity ?? 100) / 100; ctx.drawImage(im, (W - w) / 2, (H - h) / 2, w, h); ctx.restore();
  },
  paintLayers(ctx, W, H, d, s) {
    const boxes = [];
    for (const [i, L] of (d.layers || []).entries()) {
      const x = L.x * W, y = L.y * H; let box = null;
      ctx.save(); ctx.translate(x, y); if (L.rotate) ctx.rotate(L.rotate * Math.PI / 180);
      const paintStyle = (w, h) => L.metal ? this.metal(ctx, -w / 2, -h / 2, w, h, L.color && L.color !== "#b8892b" ? [this.shade(L.color, -45), this.shade(L.color, 60), L.color, this.shade(L.color, 75), this.shade(L.color, -30)] : GOLD) : (L.color || "#1e3a5f");
      if (L.type === "text") {
        const fs = (L.size || 40) * s; ctx.font = `${L.bold ? "700 " : ""}${L.italic ? "italic " : ""}${fs}px "${L.font || "Frank Ruhl Libre"}", "David", serif`;
        ctx.direction = /[\u0590-\u05FF]/.test(L.text || "") ? "rtl" : "ltr"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
        const lines = String(L.text || "").split("\n"); const w = Math.max(...lines.map(t => ctx.measureText(t).width), 10), h = fs * 1.2 * lines.length;
        if (L.shadow) { ctx.shadowColor = "rgba(0,0,0,.55)"; ctx.shadowBlur = fs * .12; ctx.shadowOffsetX = fs * .04; ctx.shadowOffsetY = fs * .05; }
        ctx.fillStyle = paintStyle(w, h);
        lines.forEach((t, k) => ctx.fillText(t, 0, (k - (lines.length - 1) / 2) * fs * 1.2));
        if (L.outline) { ctx.shadowColor = "transparent"; ctx.lineWidth = Math.max(1, fs * .03); ctx.strokeStyle = L.outline; lines.forEach((t, k) => ctx.strokeText(t, 0, (k - (lines.length - 1) / 2) * fs * 1.2)); }
        box = [w, h];
      } else if (L.type === "image") {
        const im = this.img(L.src); const w = (L.w || .4) * W;
        if (im) { const h = w * im.naturalHeight / im.naturalWidth; ctx.globalAlpha = (L.opacity ?? 100) / 100;
          if (L.round) { ctx.beginPath(); ctx.ellipse(0, 0, w / 2, h / 2, 0, 0, 7); ctx.clip(); }
          ctx.drawImage(im, -w / 2, -h / 2, w, h);
          if (L.border) { ctx.globalAlpha = 1; ctx.lineWidth = 4 * s; ctx.strokeStyle = paintStyle(w, h); if (L.round) { ctx.beginPath(); ctx.ellipse(0, 0, w / 2, h / 2, 0, 0, 7); ctx.stroke(); } else ctx.strokeRect(-w / 2, -h / 2, w, h); }
          box = [w, h]; } else box = [w, w];
      } else if (L.type === "orn") {
        const r = (L.size || 30) * s; ctx.fillStyle = ctx.strokeStyle = paintStyle(r * 2, r * 2);
        if (L.kind === "flourish") this.flourish(ctx, -r, -r, 1, 1, r / 45);
        else if (L.kind === "diamond") this.diamond(ctx, 0, 0, r);
        else if (L.kind === "luchos") this.luchosDraw(ctx, 0, 0, r);
        else if (L.kind === "fan") this.fan(ctx, 0, r * .4, r * 1.3);
        else this[L.kind] && this[L.kind](ctx, 0, 0, r);
        box = [r * 2.4, r * 2.4];
      } else if (L.type === "shape") {
        const w = (L.w || .5) * W, h = L.kind === "line" ? 0 : (L.h || .1) * H; ctx.lineWidth = (L.width || 3) * s;
        ctx.fillStyle = ctx.strokeStyle = paintStyle(w, Math.max(h, 10)); ctx.globalAlpha = (L.opacity ?? 100) / 100;
        if (L.kind === "line") { ctx.beginPath(); ctx.moveTo(-w / 2, 0); ctx.lineTo(w / 2, 0); ctx.stroke(); }
        else { ctx.beginPath(); if (L.kind === "ellipse") ctx.ellipse(0, 0, w / 2, h / 2, 0, 0, 7); else ctx.rect(-w / 2, -h / 2, w, h); L.fill ? ctx.fill() : ctx.stroke(); }
        box = [w, Math.max(h, 16 * s)];
      }
      if (box && this._screen && i === this.sel) { ctx.setLineDash([6, 4]); ctx.lineWidth = 1.5; ctx.strokeStyle = "#e11d48"; ctx.globalAlpha = 1; ctx.shadowColor = "transparent"; ctx.strokeRect(-box[0] / 2 - 6, -box[1] / 2 - 6, box[0] + 12, box[1] + 12); }
      ctx.restore();
      boxes.push(box ? [x - box[0] / 2, y - box[1] / 2, box[0], box[1]] : null);
    }
    if (this._screen) this._boxes = boxes;
  },
  frontOffset() { const { front, spine } = this.dims(1); return this.d.wrap ? front + spine : 0; },
  initDesign(el) {
    const c = $("#cvCan", el), d = () => this.d;
    const pos = e => { const r = c.getBoundingClientRect(); return [(e.clientX - r.left) / r.width * c.width - this.frontOffset(), (e.clientY - r.top) / r.height * c.height]; };
    let drag = null;
    c.addEventListener("mousedown", e => {
      const [x, y] = pos(e); const b = this._boxes || []; let hit = -1;
      for (let i = b.length - 1; i >= 0; i--) if (b[i] && x >= b[i][0] - 8 && x <= b[i][0] + b[i][2] + 8 && y >= b[i][1] - 8 && y <= b[i][1] + b[i][3] + 8) { hit = i; break; }
      this.sel = hit; if (hit >= 0) { const L = d().layers[hit]; drag = [x, y, L.x, L.y]; c.style.cursor = "grabbing"; }
      this.layerPanel(); this.draw();
    });
    window.addEventListener("mousemove", e => {
      if (!drag || this.sel < 0) return; const [x, y] = pos(e); const { front, H } = this.dims(1); const W = this.d.wrap ? front : this.dims(1).W;
      const L = d().layers[this.sel]; L.x = Math.min(1, Math.max(0, drag[2] + (x - drag[0]) / W)); L.y = Math.min(1, Math.max(0, drag[3] + (y - drag[1]) / H)); this.draw();
    });
    window.addEventListener("mouseup", () => { if (drag) { drag = null; c.style.cursor = ""; this.layerPanel(); } });
    document.addEventListener("keydown", e => {
      if (App.current !== "cover" || this.sel < 0 || App.isTypingTarget(e.target)) return;
      const L = d().layers[this.sel]; if (!L) return; const step = e.shiftKey ? .02 : .004;
      if (e.key === "Delete" || e.key === "Backspace") { d().layers.splice(this.sel, 1); this.sel = -1; }
      else if (e.key === "ArrowLeft") L.x -= step; else if (e.key === "ArrowRight") L.x += step; else if (e.key === "ArrowUp") L.y -= step; else if (e.key === "ArrowDown") L.y += step; else return;
      e.preventDefault(); this.layerPanel(); this.draw();
    });
    const add = L => { d().layers.push({ x: .5, y: .5, ...L }); this.sel = d().layers.length - 1; this.layerPanel(); this.draw(); };
    $("#cvAddText", el).onclick = () => add({ type: "text", text: "טקסט שלי", font: this.d.titleFont || "Frank Ruhl Libre", size: 48, color: "#b8892b", metal: true, shadow: true, bold: true });
    $("#cvAddOrn", el).onchange = e => { if (e.target.value) add({ type: "orn", kind: e.target.value, size: 30, color: "#b8892b", metal: true }); e.target.value = ""; };
    $("#cvAddShape", el).onchange = e => { if (e.target.value) add({ type: "shape", kind: e.target.value, w: .6, h: .12, color: "#b8892b", metal: true, fill: false, width: 3 }); e.target.value = ""; };
    $("#cvAddImg", el).onclick = async () => { const f = (await App.pickFiles("image/*", false))[0]; if (f) add({ type: "image", src: await this.fileToData(f), w: .5, opacity: 100 }); };
    $("#cvBgImg", el).onclick = async () => { const f = (await App.pickFiles("image/*", false))[0]; if (f) { this.d.bgImage = await this.fileToData(f, 2400); this.draw(); } };
    $("#cvBgNo", el).onclick = () => { this.d.bgImage = null; this.draw(); };
    this.sel = -1; this.layerPanel();
  },
  fileToData(file, max = 1600) {
    return new Promise(res => { const r = new FileReader(); r.onload = () => { const im = new Image(); im.onload = () => {
      const k = Math.min(1, max / Math.max(im.width, im.height)); const c = document.createElement("canvas"); c.width = im.width * k; c.height = im.height * k;
      c.getContext("2d").drawImage(im, 0, 0, c.width, c.height); res(c.toDataURL(/png/i.test(file.type) ? "image/png" : "image/jpeg", .9)); }; im.src = r.result; }; r.readAsDataURL(file); });
  },
  layerPanel() {
    const ls = this.d.layers || [], el = $("#cvLayers"); if (!el) return;
    const label = L => L.type === "text" ? "✏️ " + esc(String(L.text).slice(0, 24)) : L.type === "image" ? "🖼 picture" : L.type === "orn" ? "✦ " + L.kind : "▭ " + L.kind;
    el.innerHTML = ls.map((L, i) => `<div class="list-item row small" data-i="${i}" style="${i === this.sel ? "background:var(--accent-soft)" : ""}"><span style="flex:1">${label(L)}</span><a href="#" data-up="${i}" title="bring forward">▲</a><a href="#" data-dn="${i}" title="send back">▼</a><a href="#" data-cp="${i}" title="duplicate">⧉</a><a href="#" data-rm="${i}" title="delete">✕</a></div>`).join("");
    el.onclick = e => { const t = e.target; e.preventDefault();
      const i = +(t.dataset.up ?? t.dataset.dn ?? t.dataset.cp ?? t.dataset.rm ?? t.closest("[data-i]")?.dataset.i ?? -1); if (i < 0) return;
      if (t.dataset.up && i < ls.length - 1) { [ls[i], ls[i + 1]] = [ls[i + 1], ls[i]]; this.sel = i + 1; }
      else if (t.dataset.dn && i > 0) { [ls[i], ls[i - 1]] = [ls[i - 1], ls[i]]; this.sel = i - 1; }
      else if (t.dataset.cp) { ls.push({ ...ls[i], x: ls[i].x + .03, y: ls[i].y + .03 }); this.sel = ls.length - 1; }
      else if (t.dataset.rm) { ls.splice(i, 1); this.sel = -1; } else this.sel = i;
      this.layerPanel(); this.draw(); };
    const L = ls[this.sel], P = $("#cvProps"); if (!L) { P.innerHTML = ""; return; }
    const fonts = App.fontList();
    const f = (k, lbl, html) => `<label class="small" style="display:block;margin-top:4px">${lbl} ${html}</label>`;
    const num = (k, min, max, st = 1) => `<input type="range" data-k="${k}" min="${min}" max="${max}" step="${st}" value="${L[k] ?? 0}" style="width:150px">`;
    P.innerHTML = `<div class="card" style="padding:8px;margin-top:6px">` +
      (L.type === "text" ? f("text", "Text", `<textarea data-k="text" class="he-input" style="min-height:50px" dir="auto">${esc(L.text)}</textarea>`) +
        f("font", "Font", `<select data-k="font">${fonts.map(x => `<option ${x === L.font ? "selected" : ""}>${esc(x)}</option>`).join("")}</select>`) + f("size", "Size", num("size", 8, 200)) +
        f("b", "", `<input type="checkbox" data-k="bold" ${L.bold ? "checked" : ""} style="width:auto"> bold <input type="checkbox" data-k="italic" ${L.italic ? "checked" : ""} style="width:auto"> italic <input type="checkbox" data-k="shadow" ${L.shadow ? "checked" : ""} style="width:auto"> shadow`) +
        f("outline", "Outline colour", `<input type="color" data-k="outline" value="${L.outline || "#000000"}"> <a href="#" data-clear="outline">none</a>`) : "") +
      (L.type === "image" ? f("w", "Width", num("w", .05, 1.2, .01)) + f("opacity", "Opacity", num("opacity", 5, 100)) + f("r", "", `<input type="checkbox" data-k="round" ${L.round ? "checked" : ""} style="width:auto"> oval frame <input type="checkbox" data-k="border" ${L.border ? "checked" : ""} style="width:auto"> border`) : "") +
      (L.type === "orn" ? f("size", "Size", num("size", 5, 150)) : "") +
      (L.type === "shape" ? f("w", "Width", num("w", .02, 1.2, .01)) + f("h", "Height", num("h", .01, 1, .01)) + f("width", "Line", num("width", 1, 20)) + f("opacity", "Opacity", num("opacity", 5, 100)) + f("fill", "", `<input type="checkbox" data-k="fill" ${L.fill ? "checked" : ""} style="width:auto"> filled`) : "") +
      (L.type !== "image" || L.border ? f("color", "Colour", `<input type="color" data-k="color" value="${L.color || "#b8892b"}"> <input type="checkbox" data-k="metal" ${L.metal ? "checked" : ""} style="width:auto"> metallic`) : "") +
      f("rotate", "Rotate", num("rotate", -180, 180)) + `</div>`;
    P.oninput = e => { const k = e.target.dataset.k; if (!k) return; L[k] = e.target.type === "checkbox" ? e.target.checked : e.target.type === "range" ? +e.target.value : e.target.value; this.draw(); if (e.target.type === "checkbox") this.layerPanel(); };
    P.onclick = e => { if (e.target.dataset.clear) { e.preventDefault(); L[e.target.dataset.clear] = ""; this.draw(); } };
  },
  async save() { this.read(); const r = await App.api("ud_save", { table: "covers", row: { id: this.d.id, title: this.d.title || "Cover", data: JSON.stringify(this.d) } }); this.d.id = r.id; App.toast("Cover saved"); },
  async load(id) { const c = await App.api("ud_get", { table: "covers", id }); this.d = { ...this.defaults(), ...JSON.parse(c.data), id: c.id }; this.fill(); this.draw(); },
  hiRes() { const c = document.createElement("canvas"); const { W, H } = this.dims(3); c.width = W; c.height = H; this._screen = false; this.paintFull(c.getContext("2d"), 3); this._screen = true; return c; },
  exportPng() { const c = this.hiRes(); const a = document.createElement("a"); a.href = c.toDataURL("image/png"); a.download = (this.d.title || "cover") + ".png"; a.click(); },
  print() {
    const c = this.hiRes(); const img = new Image(); img.src = c.toDataURL("image/png"); img.className = "print-area"; img.style.width = "100%";
    const [w, h] = SIZES[this.d.size]; const st = document.createElement("style"); st.textContent = `@page{size:${this.d.wrap ? (2 * w + .9) : w}in ${h}in;margin:0}`;
    document.head.appendChild(st); document.body.appendChild(img); img.onload = () => { window.print(); setTimeout(() => { img.remove(); st.remove(); }, 500); };
  }
};
App.register("cover", { title: "Covers", icon: "📕", full: true, render(el) { Cover.render(el); } });
