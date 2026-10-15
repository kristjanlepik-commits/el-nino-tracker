import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { scroll, animate } from "motion";

// Scene 5 of "How a flood is made" (D-327): the pump, the fuel and the
// trigger. Every layer is drawn from pump.json, which
// design/make_explainer_assets.py builds from FLO's payload.
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const root = document.getElementById("pump");
const D = await (await fetch("assets/pump.json")).json();
const [LON0, LON1] = D.extent.lon, [LAT0, LAT1] = D.extent.lat;
const KX = Math.cos((LAT0 + LAT1) / 2 * Math.PI / 180) / 10, KZ = 1 / 10;   // units per degree
const W = (LON1 - LON0) * KX, H = (LAT1 - LAT0) * KZ;
const X = lo => (lo - (LON0 + LON1) / 2) * KX, Z = la => -(la - (LAT0 + LAT1) / 2) * KZ;
const Y_WIND = 0.16, Y_COLD = 0.62, SLAB = 0.06;

const canvas = document.getElementById("pump-gl");
const R = new THREE.WebGLRenderer({ canvas, antialias: true });
R.setPixelRatio(Math.min(devicePixelRatio, 2));
R.toneMapping = THREE.ACESFilmicToneMapping; R.toneMappingExposure = 1.0;
R.outputColorSpace = THREE.SRGBColorSpace;
R.shadowMap.enabled = true; R.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const paper = new THREE.Color("#F1F0EC");
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
slabMats.splice(2, 0, new THREE.MeshStandardMaterial({ map: tex(D.sea.img), roughness: 0.75 }));
slabMats.splice(3, 0, new THREE.MeshStandardMaterial({ color: 0xE7E6DF }));
const slab = new THREE.Mesh(new THREE.BoxGeometry(W, SLAB, H), slabMats);
slab.position.y = -SLAB / 2; slab.receiveShadow = true; slab.castShadow = true; scene.add(slab);
const sh = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.ShadowMaterial({ opacity: 0.08 }));
sh.rotation.x = -Math.PI / 2; sh.position.y = -SLAB - 0.001; sh.receiveShadow = true; scene.add(sh);

// the cold layer, two planes crossfading between ERA5 frames
const coldTex = D.cold.frames.map(f => tex(f.img));
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

// winds at 850 hPa: particles advected through the ERA5 field
const WD = D.wind, WF = WD.frames;
const t0w = Date.parse(WF[0].time), stepW = Date.parse(WF[1].time) - t0w;
function wind(lo, la, tm) {
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
const NP = reduce ? 0 : 3200;
const pts = Array.from({ length: NP }, () => spawn({}));
function spawn(p) { p.lo = LON0 + Math.random() * (LON1 - LON0); p.la = LAT0 + Math.random() * (LAT1 - LAT0);
  p.age = 0; p.life = 1.5 + Math.random() * 2.5; p.tlo = p.lo; p.tla = p.la; return p; }
const wpos = new Float32Array(Math.max(NP, 1) * 6), wcol = new Float32Array(Math.max(NP, 1) * 6);
const wgeo = new THREE.BufferGeometry();
wgeo.setAttribute("position", new THREE.BufferAttribute(wpos, 3)); wgeo.setAttribute("color", new THREE.BufferAttribute(wcol, 3));
const wmat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0 });
const wlines = new THREE.LineSegments(wgeo, wmat); wlines.frustumCulled = false; scene.add(wlines);
const INK = new THREE.Color("#1A1A18"), BG = new THREE.Color("#F1F0EC");

// time is the scroll
const frames = D.cold.frames, T0 = Date.parse(frames[0].time);
const TEND = Date.parse(WF[WF.length - 1].time), stepC = Date.parse(frames[1].time) - T0;
let tm = reduce ? TEND : T0;
if (!reduce) scroll(p => {
  const q = Math.min(1, Math.max(0, (p - 0.06) / 0.86));
  tm = T0 + q * (TEND - T0);
}, { target: root });
if (!reduce) root.querySelectorAll(".step p").forEach(el => scroll(
  animate(el, { opacity: [0, 1, 1, 0], transform: ["translateY(24px)", "none", "none", "translateY(-24px)"] }, { ease: "linear" }),
  { target: el, offset: ["start end", "center 0.6", "center 0.45", "end 0.38"] }));

const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const whenEl = document.getElementById("pump-when"), lgw = document.getElementById("pump-lgwind");
const lbcn = document.getElementById("pump-lbcn"), lbcold = document.getElementById("pump-lbcold");
function screen(v) { const p = v.clone().project(cam);
  return [(p.x + 1) / 2 * canvas.clientWidth, (1 - p.y) / 2 * canvas.clientHeight, p.z < 1]; }

function size() { const w = canvas.clientWidth, h = canvas.clientHeight;
  R.setSize(w, h, false); cam.aspect = w / h; cam.fov = w < 700 ? 52 : 32; cam.updateProjectionMatrix(); }
addEventListener("resize", size); size();

const clock = new THREE.Clock();
let frame = function () {
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  const q = (tm - T0) / (TEND - T0);
  const a = -0.30 + 0.16 * q + (reduce ? 0 : 0.03 * Math.sin(t * 0.2));
  const r = canvas.clientWidth < 700 ? 5.6 : 4.3;
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
  const d = new Date(tm);
  whenEl.textContent = d.getUTCDate() + " " + MON[d.getUTCMonth()] + ", " + String(d.getUTCHours()).padStart(2, "0") + ":00 UTC";
  let [x, y] = screen(new THREE.Vector3(bx, Y_COLD + 0.08, bz)); lbcn.style.left = x + "px"; lbcn.style.top = y + "px";
  const c = f.coldest;
  if (c.anom_c <= -5 && c.lon >= LON0 && c.lon <= LON1) {
    [x, y] = screen(new THREE.Vector3(X(c.lon), Y_COLD, Z(c.lat)));
    lbcold.style.opacity = 1; lbcold.style.left = Math.max(70, x) + "px"; lbcold.style.top = y + "px";
    lbcold.textContent = c.anom_c.toFixed(1) + " C vs normal" + (c.on_edge ? " (edge of data)" : "");
  } else lbcold.style.opacity = 0;

  R.render(scene, cam);
  requestAnimationFrame(frame);
};
let onScreen = false, running = false;
const _frame = frame;
frame = function () { if (!onScreen) { running = false; return; } _frame(); };
new IntersectionObserver(es => { onScreen = es[0].isIntersecting;
  if (onScreen && !running) { running = true; clock.getDelta(); requestAnimationFrame(frame); } }).observe(root);
