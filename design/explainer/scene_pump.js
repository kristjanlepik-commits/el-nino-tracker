import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
// Motion is the UMD build, loaded by a classic script before this module
// (platform, 15 Oct: there is no single-file ES build at 11.11.13).
const { scroll, animate } = window.Motion;

// Scene 5 of "How a flood is made" (D-327): the pump, the fuel and the
// trigger. Every layer is drawn from pump.json, which
// design/make_explainer_assets.py builds from FLO's payload.
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
// Words on the canvas come from the page (window.I18N, set by the builder
// for the Spanish edition); English is the fallback.
const L = (k, d, v) => { let s = (window.I18N && window.I18N[k]) || d;
  if (v) for (const n in v) s = s.split("{" + n + "}").join(v[n]); return s; };
const NUM = s => (window.I18N && window.I18N.dec) ? String(s).replace(".", window.I18N.dec) : String(s);

const D = await (await fetch("assets/pump.json")).json();
const [LON0, LON1] = D.extent.lon, [LAT0, LAT1] = D.extent.lat;
const KX = Math.cos((LAT0 + LAT1) / 2 * Math.PI / 180) / 10, KZ = 1 / 10;   // units per degree
const W = (LON1 - LON0) * KX, H = (LAT1 - LAT0) * KZ;
const X = lo => (lo - (LON0 + LON1) / 2) * KX, Z = la => -(la - (LAT0 + LAT1) / 2) * KZ;
const Y_WIND = 0.16, Y_COLD = 0.62, SLAB = 0.06;

// ONE FUNCTION PER STAGE. Chapter 05 is the measured act (27 Sep to 3 Oct);
// chapter 07 opens on its own stage with ECMWF's forecast for the weekend
// (Kristjan: the weekend surfaced in 05 and again in 07, the flow was odd).
// Each .pumpstage says which acts it carries in data-acts; its elements
// are found by class inside it, so two stages never share an id.
function stage(root) {
const $ = c => root.querySelector("." + c);

const canvas = $("pg-gl");
const R = new THREE.WebGLRenderer({ canvas, antialias: true });
R.setPixelRatio(Math.min(devicePixelRatio, 2));
R.toneMapping = THREE.ACESFilmicToneMapping; R.toneMappingExposure = 1.0;
R.outputColorSpace = THREE.SRGBColorSpace;
R.shadowMap.enabled = true; R.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
// Theme-aware (VD): read the page's own paper, so dark mode is dark here too.
const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const paper = new THREE.Color(cssv("--paper") || "#F1F0EC");
scene.background = paper;
scene.environment = new THREE.PMREMGenerator(R).fromScene(new RoomEnvironment(), 0.04).texture;
const cam = new THREE.PerspectiveCamera(32, 1, 0.05, 50);
const key = new THREE.DirectionalLight(0xffffff, 1.6);
key.position.set(-2, 5, 3); key.castShadow = true; key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, { left: -3, right: 3, top: 3, bottom: -3 });
scene.add(key, new THREE.AmbientLight(0xffffff, 0.9));

const TL = new THREE.TextureLoader();
const tex = u => { const t = TL.load("assets/" + u); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };

// the map as a slab: a diorama of the western Mediterranean
const slabMats = [0,1,2,3].map(() => new THREE.MeshStandardMaterial({ color: 0xE7E6DF, roughness: 0.9 }));
const seaMat = new THREE.MeshStandardMaterial({ roughness: 0.75 });
slabMats.splice(2, 0, seaMat);
slabMats.splice(3, 0, new THREE.MeshStandardMaterial({ color: 0xE7E6DF }));
const slab = new THREE.Mesh(new THREE.BoxGeometry(W, SLAB, H), slabMats);
slab.position.y = -SLAB / 2; slab.receiveShadow = true; slab.castShadow = true; scene.add(slab);
const sh = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.ShadowMaterial({ opacity: 0.08 }));
sh.rotation.x = -Math.PI / 2; sh.position.y = -SLAB - 0.001; sh.receiveShadow = true; scene.add(sh);

// TWO ACTS on one stage. "obs": what was measured, 27 Sep to 3 Oct (ERA5).
// "wk": ECMWF's forecast for this weekend (Kristjan; FLO 3903bf41), shown
// with its run time and AEMET's own "elevada incertidumbre" beside it.
// Each act carries its own frames, wind, sea and clock; the stage, camera
// and labels are shared, so the reader sees the same machine assembling.
function mkAct(src, end) {
  const frames = src.cold.frames, WF = src.wind.frames, T0 = Date.parse(frames[0].time);
  return { frames, WD: src.wind, WF, T0, TEND: Date.parse(end || frames[frames.length - 1].time),
           stepC: Date.parse(frames[1].time) - T0, t0w: Date.parse(WF[0].time),
           stepW: Date.parse(WF[1].time) - Date.parse(WF[0].time),
           coldTex: frames.map(f => tex(f.img)), seaTex: tex(src.sea.img) };
}
const coldMat = () => new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, side: THREE.DoubleSide, opacity: 0 });
const cA = new THREE.Mesh(new THREE.PlaneGeometry(W, H), coldMat()), cB = new THREE.Mesh(new THREE.PlaneGeometry(W, H), coldMat());
for (const c of [cA, cB]) { c.rotation.x = -Math.PI / 2; c.position.y = Y_COLD; c.renderOrder = 3; scene.add(c); }
// the level it sits at: a hairline frame, so the layer reads as a height
const frameGeo = new THREE.EdgesGeometry(new THREE.PlaneGeometry(W, H)); frameGeo.rotateX(-Math.PI / 2);
const lvl = new THREE.LineSegments(frameGeo, new THREE.LineBasicMaterial({ color: 0x0A4A57, transparent: true, opacity: 0.35 }));
lvl.position.y = Y_COLD; scene.add(lvl);
// corner posts tie the level to the map
const posts = [];
for (const [sx, sz] of [[-1,-1],[1,-1],[1,1],[-1,1]]) posts.push(sx*W/2, 0, sz*H/2, sx*W/2, Y_COLD, sz*H/2);
scene.add(new THREE.LineSegments(new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(posts, 3)),
  new THREE.LineDashedMaterial({ color: 0x6E6E67, dashSize: 0.02, gapSize: 0.02, transparent: true, opacity: 0.5 })).computeLineDistances());

// Barcelona: a pin from the map through the layers
const bx = X(D.barcelona.lon), bz = Z(D.barcelona.lat);
const pin = new THREE.Mesh(new THREE.CylinderGeometry(0.003, 0.003, Y_COLD + 0.08, 6), new THREE.MeshBasicMaterial({ color: 0x1A1A18 }));
pin.position.set(bx, (Y_COLD + 0.08) / 2, bz); scene.add(pin);
const head = new THREE.Mesh(new THREE.SphereGeometry(0.014, 16, 12), new THREE.MeshStandardMaterial({ color: 0x1A1A18 }));
head.position.set(bx, 0.004, bz); scene.add(head);

// winds at 850 hPa: particles advected through the act's field
function wind(lo, la, tm) {
  const { WD, WF, t0w, stepW } = act;
  const fi = (WD.lat[0] - la) / (WD.lat[0] - WD.lat[1]), fj = (lo - WD.lon[0]) / (WD.lon[1] - WD.lon[0]);
  const i = Math.floor(fi), j = Math.floor(fj);
  if (i < 0 || j < 0 || i >= WD.lat.length - 1 || j >= WD.lon.length - 1) return null;
  const di = fi - i, dj = fj - j;
  let ft = (tm - t0w) / stepW; ft = Math.max(0, Math.min(WF.length - 1.0001, ft));
  const k = Math.floor(ft), dk = ft - k;
  const s = (g) => g[i][j]*(1-di)*(1-dj) + g[i+1][j]*di*(1-dj) + g[i][j+1]*(1-di)*dj + g[i+1][j+1]*di*dj;
  const a = WF[k], b = WF[Math.min(k + 1, WF.length - 1)];
  return [s(a.u)*(1-dk) + s(b.u)*dk, s(a.v)*(1-dk) + s(b.v)*dk];
}
// THE PAYOFF: the wind off Barcelona, as one bold arrow. Sampled from the
// same 850 hPa field as the streaks, at a sea point just off the coast,
// and shown only while it blows onshore (from the south-east quadrant),
// so the moment the story turns on is drawn rather than asserted.
// Onshore for each coast is its own sector: Barcelona's coast faces SE,
// Valencia's faces E. Sampled at FLO's own grid points (41N 3E, 39N 0E) so the
// label matches the captions. Valencia's arrow belongs to the forecast act only,
// where FLO found an easterly off Valencia; the measured act is Barcelona.
const OFFS = [{ lat: 41.0, lon: 3.0, lo: 100, hi: 165, acts: ["obs", "wk"], el: "pg-lbwind" },
              { lat: 39.0, lon: 0.0, lo: 68, hi: 140, acts: ["wk"], el: "pg-lbwind2" }];
for (const o of OFFS) {
  o.arrow = new THREE.Group();
  o.mat = new THREE.MeshStandardMaterial({ color: 0x1A1A18, transparent: true, opacity: 0, roughness: 0.5 });
  o.shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 1, 12), o.mat);
  o.tip = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.16, 20), o.mat);
  o.arrow.add(o.shaft, o.tip); scene.add(o.arrow);
  o.lb = $(o.el);
}
const COMPASS = L("compass", "N NE E SE S SW W NW").split(" ");

const NP = reduce ? 0 : 3200;
const pts = Array.from({ length: NP }, () => spawn({}));
function spawn(p) { p.lo = LON0 + Math.random() * (LON1 - LON0); p.la = LAT0 + Math.random() * (LAT1 - LAT0);
  p.age = 0; p.life = 1.5 + Math.random() * 2.5; p.tlo = p.lo; p.tla = p.la; return p; }
const wpos = new Float32Array(Math.max(NP, 1) * 6), wcol = new Float32Array(Math.max(NP, 1) * 6);
const wgeo = new THREE.BufferGeometry();
wgeo.setAttribute("position", new THREE.BufferAttribute(wpos, 3)); wgeo.setAttribute("color", new THREE.BufferAttribute(wcol, 3));
const wmat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0 });
const wlines = new THREE.LineSegments(wgeo, wmat); wlines.frustumCulled = false; scene.add(wlines);
const INK = new THREE.Color(cssv("--ink") || "#1A1A18"), BG = paper.clone();

// time is the scroll
// The measured act ends on the rain day, 3 October 12 UTC, not on the last
// frame FLO emitted: what comes after is not part of this story.
const want = (root.dataset.acts || "obs wk").split(" ");
const ACTS = {};
if (want.includes("obs")) ACTS.obs = mkAct({ cold: D.cold, wind: D.wind, sea: D.sea }, "2026-10-03T12:00Z");
if (want.includes("wk") && D.weekend) ACTS.wk = mkAct(D.weekend, "2026-10-19T12:00Z");
let actName = Object.keys(ACTS)[0], act = ACTS[actName];
root.classList.toggle("forecast", actName === "wk");
seaMat.map = act.seaTex;
let tm = reduce ? act.TEND : act.T0;
// The clock is pinned to the captions: each .step carries the moment its
// words describe (data-at) and its act (data-act); within an act the time
// is interpolated between caption plateaus, so the date on screen is the
// date in the caption (CPO).
const stepEls = [...root.querySelectorAll(".step[data-at]")];
function knots() {
  const span = root.offsetHeight - innerHeight;
  const at = el => (el.offsetTop + el.offsetHeight / 2 - innerHeight / 2) / span;
  // The cut is the "This weekend" title card, the first wk step of any kind.
  const first = root.querySelector('.step[data-act="wk"]');
  const cut = !ACTS.obs ? -1 : (first && ACTS.wk ? (first.offsetTop + first.offsetHeight * 0.25 - innerHeight * 0.5) / span : 2);
  const out = { cut };
  for (const name of Object.keys(ACTS)) {
    const A = ACTS[name], k = [];
    stepEls.filter(el => (el.dataset.act || "obs") === name).forEach(el => {
      // data-at "a/b": the clock runs a to b while this caption is read
      const [ta, tb] = el.dataset.at.split("/").map(Date.parse);
      // 0.42 of a step either side of its centre: the caption's date holds
      // for nearly all the time the caption can be read (CPO saw the clock
      // lag its caption with the 0.3 band).
      const c = at(el), hw = 0.42 * el.offsetHeight / span;
      // reach b by the middle of the caption and hold it, so the last
      // moment it names is on screen while the reader is still reading
      if (isNaN(tb)) k.push([c - hw, ta], [c + hw, ta]);
      else k.push([c - hw, ta], [c - hw * 0.1, tb], [c + hw, tb]);
    });
    const p0 = name === "wk" ? cut : 0, p1 = name === "wk" ? 1 : Math.min(1, cut);
    out[name] = [[p0, name === "wk" && k.length ? k[0][1] - 2 * A.stepC : A.T0], ...k,
                 [p1, k.length ? k[k.length - 1][1] : A.TEND]];
  }
  return out;
}
let KN = knots(); addEventListener("resize", () => { KN = knots(); });
function setAct(name) {
  if (name === actName || !ACTS[name]) return;
  actName = name; act = ACTS[name]; seaMat.map = act.seaTex; seaMat.needsUpdate = true;
  for (const p of pts) spawn(p);
  root.classList.toggle("forecast", name === "wk");
}
if (!reduce) scroll(p => {
  setAct(p >= KN.cut ? "wk" : "obs");
  const K = KN[actName];
  let i = 1; while (i < K.length - 1 && p > K[i][0]) i++;
  const [p0, t0] = K[i - 1], [p1, t1] = K[i];
  const f = p1 > p0 ? Math.min(1, Math.max(0, (p - p0) / (p1 - p0))) : 1;
  tm = Math.min(act.TEND, Math.max(act.T0, t0 + f * (t1 - t0)));
}, { target: root });
if (!reduce) root.querySelectorAll(".step p").forEach(el => scroll(
  animate(el, { opacity: [0, 1, 1, 0], transform: ["translateY(24px)", "none", "none", "translateY(-24px)"] }, { ease: "linear" }),
  { target: el, offset: ["start end", "center 0.6", "center 0.45", "end 0.38"] }));

const MON = L("mon", "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec").split(" ");
const whenEl = $("pg-when"), lgw = $("pg-lgwind");
const lbcn = $("pg-lbcn"), lbcold = $("pg-lbcold");
function screen(v) { const p = v.clone().project(cam);
  return [(p.x + 1) / 2 * canvas.clientWidth, (1 - p.y) / 2 * canvas.clientHeight, p.z < 1]; }

function size() { const w = canvas.clientWidth, h = canvas.clientHeight;
  R.setSize(w, h, false); cam.aspect = w / h; cam.fov = w < 700 ? 52 : 32; cam.updateProjectionMatrix(); }
addEventListener("resize", size); size();

const clock = new THREE.Clock();
let frame = function () {
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  const { frames, coldTex, T0, TEND, stepC, t0w, stepW } = act;
  const q = (tm - T0) / (TEND - T0);
  const a = -0.30 + 0.16 * q + (reduce ? 0 : 0.03 * Math.sin(t * 0.2));
  const r = canvas.clientWidth < 700 ? 6.6 : 5.0;
  cam.position.set(Math.sin(a) * r, 2.9 - 0.35 * q, Math.cos(a) * r);
  cam.lookAt(0, 0.22, 0.05);

  // cold layer crossfade
  let fc = (tm - T0) / stepC; fc = Math.max(0, Math.min(frames.length - 1.0001, fc));
  const k = Math.floor(fc), dk = fc - k;
  cA.material.map = coldTex[k]; cA.material.opacity = 1 - dk; cA.material.needsUpdate = true;
  cB.material.map = coldTex[k + 1]; cB.material.opacity = dk; cB.material.needsUpdate = true;
  const f = dk < 0.5 ? frames[k] : frames[k + 1];

  // winds fade in once the wind record starts
  const wOn = Math.max(0, Math.min(1, (tm - t0w + stepW) / stepW));
  wmat.opacity = 0.9 * wOn; lgw.style.opacity = wOn;
  const tSim = Math.max(tm, t0w);
  for (let n = 0; n < NP; n++) {
    const p = pts[n];
    const w = wind(p.lo, p.la, tSim);
    p.age += dt;
    if (!w || p.age > p.life || p.lo < LON0 || p.lo > LON1 || p.la < LAT0 || p.la > LAT1) { spawn(p); continue; }
    p.tlo = p.lo; p.tla = p.la;
    const kk = 0.11;
    p.lo += w[0] * kk * dt / Math.cos(p.la * Math.PI / 180); p.la += w[1] * kk * dt;
    const sp = Math.hypot(w[0], w[1]);
    const tail = 0.05 + 0.012 * sp;
    const o = n * 6;
    wpos[o] = X(p.lo); wpos[o+1] = Y_WIND; wpos[o+2] = Z(p.la);
    wpos[o+3] = X(p.lo - w[0] * tail / Math.cos(p.la * Math.PI / 180) * 0.75); wpos[o+4] = Y_WIND; wpos[o+5] = Z(p.la - w[1] * tail * 0.75);
    const fade = Math.min(1, p.age * 3, (p.life - p.age) * 3) * Math.min(1, sp / 6);
    const c = BG.clone().lerp(INK, 0.35 + 0.65 * fade);
    wcol[o] = c.r; wcol[o+1] = c.g; wcol[o+2] = c.b; wcol[o+3] = BG.r; wcol[o+4] = BG.g; wcol[o+5] = BG.b;
  }
  wgeo.attributes.position.needsUpdate = true; wgeo.attributes.color.needsUpdate = true;

  // labels
  // SNAPPED to the nearest 12-hourly field (FLO): the fields exist at 00
  // and 12 UTC only, and a clock reading 16:00 implies one that does not.
  const d = new Date(Math.round((tm - T0) / stepC) * stepC + T0);
  whenEl.textContent = d.getUTCDate() + " " + MON[d.getUTCMonth()] + ", " + String(d.getUTCHours()).padStart(2, "0") + ":00 UTC"
                     + (actName === "wk" ? " \u00b7 " + L("fc", "forecast") : "");
  let [x, y] = screen(new THREE.Vector3(bx, Y_COLD + 0.08, bz)); lbcn.style.left = x + "px"; lbcn.style.top = y + "px";
  const c = f.coldest;
  // Labelled only while it is a pool: at 8 C or more below normal. Past
  // 2 October the grid's coldest cell is an unrelated patch off Libya,
  // and pump.not_claimed rules out cold air over Barcelona on 3 October.
  if (c.anom_c <= -8 && c.lon >= LON0 && c.lon <= LON1) {
    [x, y] = screen(new THREE.Vector3(X(c.lon), Y_COLD, Z(c.lat)));
    lbcold.style.opacity = 1; // clear of the caption column on wide screens
    const minX = canvas.clientWidth >= 900 ? 470 : 150;
    lbcold.style.left = Math.min(canvas.clientWidth - 140, Math.max(minX, x)) + "px"; lbcold.style.top = y + "px";
    lbcold.textContent = L("pool", "Cold pool {v} \u00b0C vs normal", { v: NUM(c.anom_c.toFixed(1)) });
  } else lbcold.style.opacity = 0;

  // onshore arrows
  for (const o of OFFS) {
    const wb = o.acts.includes(actName) ? wind(o.lon, o.lat, tSim) : null;
    let show = 0;
    if (wb) {
      const sp = Math.hypot(wb[0], wb[1]);
      const from = (Math.atan2(-wb[0], -wb[1]) * 180 / Math.PI + 360) % 360;
      // The story's onshore flow, per coast: Barcelona a south-easterly
      // (FLO: 123 deg), Valencia an easterly. A southerly on 29 Sep is true
      // but is not it, and showing it spent the climax early (CPO).
      const onshore = from >= o.lo && from <= o.hi && sp >= 8;
      show = onshore ? 1 : 0;
      const len = 0.16 + sp * 0.045;
      const dx = wb[0] * KX, dz = -wb[1] * KZ, m = Math.hypot(dx, dz) || 1;
      const ux = dx / m, uz = dz / m;
      const sx = X(o.lon) - ux * len, sz = Z(o.lat) - uz * len;   // tail out at sea, head at the coast
      o.arrow.position.set(sx, Y_WIND + 0.02, sz);
      o.arrow.rotation.set(0, Math.atan2(ux, uz), 0);
      o.shaft.scale.y = len; o.shaft.rotation.x = Math.PI / 2; o.shaft.position.set(0, 0, len / 2);
      o.tip.rotation.x = Math.PI / 2; o.tip.position.set(0, 0, len + 0.075);
      if (show > 0 && o.lb) {
        [x, y] = screen(new THREE.Vector3(sx, Y_WIND + 0.02, sz));
        o.lb.style.top = (y + 34) + "px";
        // kept inside the stage (the label is centred on x by its transform)
        const half = (o.lb.offsetWidth || 220) / 2;
        o.lb.style.left = Math.min(canvas.clientWidth - half - 12, Math.max(half + 12, x)) + "px";
        o.lb.textContent = L("onshore", "Onshore: from the {d}, {s} m/s", { d: COMPASS[Math.round(from / 45) % 8], s: sp.toFixed(0) });
      }
    }
    o.mat.opacity = show; if (o.lb) o.lb.style.opacity = show;
  }

  R.render(scene, cam);
  requestAnimationFrame(frame);
};
let onScreen = false, running = false;
const _frame = frame;
frame = function () { if (!onScreen) { running = false; return; } _frame(); };
new IntersectionObserver(es => { onScreen = es[0].isIntersecting;
  if (onScreen && !running) { running = true; clock.getDelta(); requestAnimationFrame(frame); } }).observe(root);
}
document.querySelectorAll(".pumpstage").forEach(stage);
