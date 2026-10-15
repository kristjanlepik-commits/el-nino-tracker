import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

// Scene 7 of "How a flood is made" (D-327): the ground can't drink that
// fast. Two cut-away hillside blocks under one seeded rain. A drop soaks in
// where the soil still has room and otherwise runs downhill, trying again
// at every column it crosses; what reaches the foot of the slope fills the
// trough. The ONLY difference between the blocks is how much water the
// soil holds before the rain starts. ILLUSTRATIVE physics, labelled on the
// page: no rate, depth or share here is a measurement. The measured fact
// (FLO's topsoil ranks) sits in the table beside it.

const root = document.getElementById("ground");
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const rng = s => () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296;

const T = 16, HOLD = 3, N = 64;
const LAND = 0.72, TOP0 = 0.62, DROP = 0.18, DEPTH = 0.55, CH = 0.04;
const sy = x => TOP0 - (x / LAND) * DROP;             // surface height along the slope

const EV = (() => {                                   // one storm, both blocks
  const r = rng(20261003), ev = []; let t = 0;
  while (t < T) {
    const q = t / T, rate = 30 + 260 * Math.exp(-Math.pow((q - 0.42) / 0.14, 2));
    t += -Math.log(1 - r()) / rate; ev.push([t, r(), r()]);
  }
  return ev;
})();

class Block {
  constructor(wet, x0) { this.wet = wet; this.x0 = x0; this.reset(); }
  reset() {
    const r = rng(this.wet ? 7 : 3);
    this.S = Array.from({ length: N }, () => this.wet ? 0.66 + 0.1 * r() : 0.08 + 0.08 * r());
    this.allow = new Array(N).fill(0); this.surf = []; this.sink = []; this.river = 0; this.k = 0;
  }
  soak(c, x) {
    if (c < 0 || c >= N || this.allow[c] < 1 || this.S[c] >= 0.995) return false;
    this.allow[c] -= 1; this.S[c] = Math.min(1, this.S[c] + 0.018);
    this.sink.push({ x, y: sy(x), to: sy(x) * (1 - this.S[c]) });
    return true;
  }
  step(t, dt) {
    for (let i = 0; i < N; i++) this.allow[i] = Math.min(1.5, this.allow[i] + dt * 9 * Math.pow(1 - this.S[i], 1.6));
    const fresh = [];
    while (this.k < EV.length && EV[this.k][0] <= t) {
      const [, fx, fz] = EV[this.k++]; const x = fx;
      // Rain straight onto the channel counts lightly: at full weight it
      // filled the dry block's river almost as high as the wet one's and
      // hid the difference the scene exists to show (Kristjan, 16 Oct).
      if (x >= LAND) this.river += 0.15;
      else if (!this.soak(Math.floor(x / LAND * N), x)) this.surf.push({ x, z: fz });
      fresh.push([x, fz]);
    }
    const keep = [];
    for (const s of this.surf) {
      const c0 = Math.floor(s.x / LAND * N); s.x += 0.34 * dt;   // fast: runoff reaches the river within the storm (Kristjan)
      const c1 = Math.floor(s.x / LAND * N);
      if (s.x >= LAND) { this.river++; continue; }
      if (c1 !== c0 && this.soak(c1, s.x)) continue;
      keep.push(s);
    }
    this.surf = keep;
    this.sink = this.sink.filter(p => (p.y -= 0.3 * dt) > p.to);
    return fresh;
  }
  riverH() { return Math.min(0.34, this.river * 0.0005); }
}

// The cross-section texture: the block's front face, redrawn each frame.
function drawSection(ctx, b, C) {
  const W = ctx.canvas.width, H = ctx.canvas.height;
  const px = x => x / LAND * W, py = y => H - y / TOP0 * H;
  ctx.fillStyle = C.land; ctx.fillRect(0, 0, W, H);
  // soil texture: fixed speckle, so it reads as ground rather than a fill
  ctx.fillStyle = C.grain;
  for (const [gx, gy, gr] of GRAIN) { ctx.beginPath(); ctx.arc(gx * W, gy * H, gr, 0, 6.3); ctx.fill(); }
  ctx.globalAlpha = 0.62; ctx.fillStyle = C.flood;
  ctx.beginPath(); ctx.moveTo(0, py(sy(0)));
  for (let i = 0; i < N; i++) {
    const a = b.S[Math.max(0, i - 1)], m = b.S[i], c = b.S[Math.min(N - 1, i + 1)];
    const x = (i + 0.5) * LAND / N; ctx.lineTo(px(x), py(sy(x)));
  }
  for (let i = N - 1; i >= 0; i--) {
    const a = b.S[Math.max(0, i - 1)], m = b.S[i], c = b.S[Math.min(N - 1, i + 1)];
    const x = (i + 0.5) * LAND / N; ctx.lineTo(px(x), py(sy(x) * (1 - (a + 2 * m + c) / 4)));
  }
  ctx.closePath(); ctx.fill(); ctx.globalAlpha = 1;
  ctx.fillStyle = C.flood;
  for (const p of b.sink) ctx.fillRect(px(p.x) - 1.5, py(p.y), 3, 7);
  // clear the sky above the slope: the texture covers the whole cap
  ctx.fillStyle = "rgba(0,0,0,0)";
}
const GRAIN = (() => { const r = rng(11); return Array.from({ length: 260 }, () => [r(), r(), 0.8 + r() * 1.6]); })();

const canvas = document.getElementById("ground-gl");
const R = new THREE.WebGLRenderer({ canvas, antialias: true });
R.setPixelRatio(Math.min(devicePixelRatio, 2));
R.toneMapping = THREE.ACESFilmicToneMapping; R.outputColorSpace = THREE.SRGBColorSpace;
R.shadowMap.enabled = true; R.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const paper = new THREE.Color(css("--paper")), stormC = new THREE.Color("#c9ccca");
scene.background = paper.clone();
scene.environment = new THREE.PMREMGenerator(R).fromScene(new RoomEnvironment(), 0.04).texture;
const cam = new THREE.PerspectiveCamera(30, 1, 0.05, 40);
const key = new THREE.DirectionalLight(0xffffff, 1.7);
key.position.set(-2, 5, 4); key.castShadow = true; key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, { left: -3, right: 3, top: 3, bottom: -3 });
scene.add(key, new THREE.AmbientLight(0xffffff, 0.85));
const floor = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.ShadowMaterial({ opacity: 0.08 }));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

// Earth, not paper: the site's --land grey read as an empty box. A muted
// soil tone keeps to the palette's warmth without a new hue family.
const C = { land: "#C2B497", flood: css("--flood"), grain: "rgba(92,74,48,.30)" };
const flood = new THREE.Color(C.flood);

function makeBlock(b) {
  const g = new THREE.Group(); g.position.x = b.x0;
  const shape = new THREE.Shape([new THREE.Vector2(0, 0), new THREE.Vector2(LAND, 0),
    new THREE.Vector2(LAND, sy(LAND)), new THREE.Vector2(0, sy(0))]);
  const geo = new THREE.ExtrudeGeometry(shape, { depth: DEPTH, bevelEnabled: false });
  // caps carry UVs in shape units; scale them onto the unit texture
  const uv = geo.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) / LAND, uv.getY(i) / TOP0);
  const cv = document.createElement("canvas"); cv.width = 512; cv.height = 384;
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const capMat = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.95 });
  const sideMat = new THREE.MeshStandardMaterial({ color: 0xA99C80, roughness: 0.95 });
  const mesh = new THREE.Mesh(geo, [capMat, sideMat]);
  mesh.position.z = -DEPTH / 2;          // extruded along +z; front cap faces the camera
  mesh.castShadow = mesh.receiveShadow = true;
  g.add(mesh);
  // the trough at the foot of the slope, and the water in it
  const tw = 1 - LAND;
  const trough = new THREE.Mesh(new THREE.BoxGeometry(tw, CH, DEPTH),
    new THREE.MeshStandardMaterial({ color: 0xC9C8BE, roughness: 0.9 }));
  trough.position.set(LAND + tw / 2, CH / 2, 0); trough.receiveShadow = true; g.add(trough);
  const water = new THREE.Mesh(new THREE.BoxGeometry(tw * 0.96, 1, DEPTH * 0.96),
    new THREE.MeshPhysicalMaterial({ color: flood.clone().offsetHSL(0, 0.1, 0.06), roughness: 0.08, clearcoat: 1,
      emissive: flood, emissiveIntensity: 0.25, transparent: true, opacity: 0.95 }));
  water.position.set(LAND + tw / 2, CH, 0); g.add(water);
  const edge = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(tw, 0.36, DEPTH)),
    new THREE.LineBasicMaterial({ color: 0x3A3A36, transparent: true, opacity: 0.55 }));
  edge.position.set(LAND + tw / 2, CH + 0.18, 0); g.add(edge);
  // running water on the surface
  const NS = 600, sp = new Float32Array(NS * 3);
  const sgeo = new THREE.BufferGeometry(); sgeo.setAttribute("position", new THREE.BufferAttribute(sp, 3));
  const sm = new THREE.Points(sgeo, new THREE.PointsMaterial({ color: flood, size: 0.018, transparent: true, opacity: 0.95 }));
  sm.frustumCulled = false; g.add(sm);
  scene.add(g);
  return { g, cv, ctx: cv.getContext("2d"), tex, water, sgeo, sp, NS, tw };
}

const blocks = [new Block(false, -1.3), new Block(true, 0.22)];
const views = blocks.map(makeBlock);

// rain: streaks over both blocks, from the same events
const NR = reduce ? 1 : 700;
const rain = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.0025, 0.0025, 0.09, 4),
  new THREE.MeshBasicMaterial({ color: flood, transparent: true, opacity: 0.6 }), NR);
rain.frustumCulled = false; scene.add(rain);
let drops = [];
const M = new THREE.Matrix4();

const clockEl = document.getElementById("ground-clock");
const riverEls = [...root.querySelectorAll(".g3-river")];
const labEls = [root.querySelector(".g3-dry"), root.querySelector(".g3-wet")];
function toScreen(v3) { const p = v3.clone().project(cam);
  return [(p.x + 1) / 2 * canvas.clientWidth, (1 - p.y) / 2 * canvas.clientHeight]; }
function size() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  R.setSize(w, h, false); cam.aspect = w / h; cam.fov = w < 700 ? 46 : 30; cam.updateProjectionMatrix();
}
addEventListener("resize", size); size();

let t0 = null, last = null, on = false;
function frame(ts) {
  if (!on) { last = null; return; }
  if (t0 === null) t0 = ts;
  const dt = last === null ? 0 : Math.min(0.05, (ts - last) / 1000); last = ts;
  let t = (ts - t0) / 1000;
  if (t > T + HOLD) { t0 = ts; t = 0; blocks.forEach(b => b.reset()); drops = []; }
  const tt = reduce ? T : Math.min(t, T);
  const q = tt / T, intensity = Math.exp(-Math.pow((q - 0.42) / 0.16, 2));
  scene.background.copy(paper).lerp(stormC, 0.22 * intensity * (t <= T ? 1 : 0));

  blocks.forEach((b, i) => {
    const fresh = (reduce || t <= T + 1.5) ? b.step(tt, dt) : [];
    if (i === 0) for (const [fx, fz] of fresh) if (drops.length < NR) drops.push({ fx, fz, y: 1.05 + Math.random() * 0.3 });
    const v = views[i];
    drawSection(v.ctx, b, C); v.tex.needsUpdate = true;
    const h = b.riverH(); v.water.scale.y = Math.max(h, 0.0005); v.water.position.y = CH + h / 2;
    let n = 0;
    for (const s of b.surf) {
      if (n >= v.NS) break;
      v.sp[n * 3] = s.x; v.sp[n * 3 + 1] = sy(s.x) + 0.008; v.sp[n * 3 + 2] = (s.z - 0.5) * DEPTH * 0.95; n++;
    }
    v.sgeo.setDrawRange(0, n); v.sgeo.attributes.position.needsUpdate = true;
  });

  // rain streaks: each falls over BOTH blocks at the same (x, z), the same storm
  let r = 0; const keep = [];
  for (const d of drops) {
    d.y -= 2.6 * dt;
    const ground = d.fx < LAND ? sy(d.fx) : CH;
    if (d.y < ground) continue;
    keep.push(d);
    for (const v of views) {
      if (r >= NR) break;
      M.makeTranslation(v.g.position.x + d.fx, d.y, (d.fz - 0.5) * DEPTH * 0.95); rain.setMatrixAt(r++, M);
    }
  }
  drops = keep; rain.count = r; rain.instanceMatrix.needsUpdate = true;

  // From the front-right, so both rivers (at each block's downhill, +x
  // end) face the reader and nothing is cut at the frame edge (Kristjan).
  const a = 0.42 + 0.03 * Math.sin(ts / 5000);
  const narrow = canvas.clientWidth < 700;
  const rad = narrow ? 5.0 : 3.35;
  cam.position.set(-0.05 + Math.sin(a) * rad, narrow ? 1.9 : 1.55, Math.cos(a) * rad);
  cam.lookAt(-0.05, 0.22, 0);
  cam.updateMatrixWorld();
  views.forEach((v, i) => { const lab = labEls[i]; if (!lab) return;
    const [x, y] = toScreen(new THREE.Vector3(v.g.position.x + 0.05, TOP0 + 0.5, DEPTH / 2));
    // Never above the stage: the label would sit on the paragraph (CPO).
    lab.style.left = x + "px"; lab.style.top = Math.max(64, y) + "px"; });
  views.forEach((v, i) => { const el = riverEls[i]; if (!el) return;
    const [x, y] = toScreen(new THREE.Vector3(v.g.position.x + LAND + v.tw / 2, CH + 0.4, DEPTH / 2));
    el.style.left = x + "px"; el.style.top = y + "px"; });
  if (clockEl) clockEl.textContent = "Hour " + Math.round(24 * tt / T) + " of 24";
  R.render(scene, cam);
  if (!reduce) requestAnimationFrame(frame);
}
new IntersectionObserver(es => {
  const was = on; on = es[0].isIntersecting;
  if (on && !was) requestAnimationFrame(frame);
}, { threshold: 0.2 }).observe(root);

// ?still=SECONDS renders the scene at that moment of the storm, once, with
// no animation loop: for screenshots and share cards, and for checking the
// scene in a browser that is not painting frames.
const still = parseFloat(new URLSearchParams(location.search).get("still"));
if (still >= 0) {
  on = true;
  for (let ms = 0; ms <= still * 1000; ms += 1000 / 60) frame(ms);
  on = false;
}
