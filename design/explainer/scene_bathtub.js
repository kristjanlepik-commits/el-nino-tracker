import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { scroll, animate } from "motion";

// Scene 1 of "How a flood is made" (D-327). The section carries its own
// measured value in data-mm, so this module holds no number of its own.
const root = document.getElementById("bath");
const MM = parseFloat(root.dataset.mm), D = MM / 1000;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

const canvas = document.getElementById("bath-gl");
const R = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
R.setPixelRatio(Math.min(devicePixelRatio, 2));
R.toneMapping = THREE.ACESFilmicToneMapping; R.toneMappingExposure = 1.0;
R.shadowMap.enabled = true; R.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
const paper = new THREE.Color(css("--paper")), storm = new THREE.Color("#c9ccca");
scene.background = paper.clone();
scene.fog = new THREE.Fog(paper.clone(), 6, 14);
const pm = new THREE.PMREMGenerator(R);
scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;

const cam = new THREE.PerspectiveCamera(30, 1, 0.1, 50);

// light: one soft key from upper left, so the glass catches an edge
const key = new THREE.DirectionalLight(0xffffff, 2.2);
key.position.set(-2, 7, 2.5); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 6;
Object.assign(key.shadow.camera, { left: -2, right: 2, top: 2, bottom: -2 });
scene.add(key, new THREE.AmbientLight(0xffffff, 0.35));

// ground
const ground = new THREE.Mesh(new THREE.PlaneGeometry(30, 30),
  new THREE.ShadowMaterial({ opacity: 0.10 }));
ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
const floorTile = new THREE.Mesh(new THREE.PlaneGeometry(1, 1),
  new THREE.MeshStandardMaterial({ color: 0xd9d8d0, roughness: 0.95 }));
floorTile.rotation.x = -Math.PI / 2; floorTile.position.y = 0.001; floorTile.receiveShadow = true;
scene.add(floorTile);

// the glass cube: physical transmission, plus hairline edges in ink
// Glass as reflection only: a thin sheen that catches the room light on
// its faces, nearly clear straight through, so the water reads inside it.
const glass = new THREE.Mesh(new RoundedBoxGeometry(1.02, 1.0, 1.02, 4, 0.01),
  new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.02, metalness: 0,
    clearcoat: 1, clearcoatRoughness: 0.02, envMapIntensity: 1.4,
    transparent: true, opacity: 0.10, depthWrite: false, side: THREE.DoubleSide }));
glass.position.y = 0.5; glass.renderOrder = 2; scene.add(glass);
const edges = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(1.02, 1, 1.02)),
  new THREE.LineBasicMaterial({ color: css("--ink-faint"), transparent: true, opacity: 0.55 }));
edges.position.y = 0.5; scene.add(edges);

// ruler: a tick every 5 cm on the front-right edge, heavier every 10
const tickMat = new THREE.LineBasicMaterial({ color: css("--ink") });
const tg = [];
for (let cm = 0; cm <= 100; cm += 5) {
  const y = cm / 100, len = cm % 10 === 0 ? 0.05 : 0.025;
  tg.push(0.51, y, 0.51, 0.51 + len, y, 0.51);
}
const ticks = new THREE.LineSegments(new THREE.BufferGeometry().setAttribute("position",
  new THREE.Float32BufferAttribute(tg, 3)), tickMat);
scene.add(ticks);

// water: a body plus a rippling surface
const flood = new THREE.Color(css("--flood"));
const waterMat = new THREE.MeshPhysicalMaterial({ color: flood, roughness: 0.15, metalness: 0,
  clearcoat: 0.6, transparent: true, opacity: 0.78, envMapIntensity: 0.8 });
const body = new THREE.Mesh(new THREE.BoxGeometry(0.995, 1, 0.995), waterMat);
body.position.y = 0; body.castShadow = true; body.renderOrder = 1; scene.add(body);
const SEG = 110;
const surfGeo = new THREE.PlaneGeometry(0.995, 0.995, SEG, SEG); surfGeo.rotateX(-Math.PI / 2);
// Soft, not mirror: a sharp clearcoat turned the room's light boxes into a
// camouflage pattern. Broad highlight from the key light, gentle sheen.
const surf = new THREE.Mesh(surfGeo, new THREE.MeshPhysicalMaterial({ color: flood.clone().offsetHSL(0, -0.04, 0.08),
  roughness: 0.42, metalness: 0.0, sheen: 0.4, sheenColor: new THREE.Color(0xffffff),
  envMapIntensity: 0.55, transparent: true, opacity: 0.93 }));
surf.renderOrder = 1;
scene.add(surf);
const base = surfGeo.attributes.position.array.slice();

// rain: instanced streaks inside and above the cube
const N = reduce ? 0 : 420;
const drop = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.0035, 0.0035, 0.16, 4),
  new THREE.MeshBasicMaterial({ color: flood, transparent: true, opacity: 0.6 }), Math.max(N, 1));
drop.frustumCulled = false; scene.add(drop);
const P = Array.from({ length: N }, () => ({ x: Math.random() - 0.5, z: Math.random() - 0.5,
  y: 1 + Math.random() * 3, v: 3.2 + Math.random() * 1.2 }));
// splash rings where drops land
const RINGS = reduce ? 0 : 40;
const ringGeo = new THREE.RingGeometry(0.9, 1, 24); ringGeo.rotateX(-Math.PI / 2);
const rings = Array.from({ length: RINGS }, () => {
  const m = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0 }));
  m.userData.t = 1; scene.add(m); return m;
});
let ri = 0;

let level = reduce ? D : 0, rate = 0;
const num = document.getElementById("bath-num"), unit = document.getElementById("bath-unit");

// SCROLL DRIVES THE STORM. Progress through the section maps to the day;
// rain intensity peaks mid-section, and the level is the integral, so the
// cube fills exactly to 159.1 mm by the end, never past it.
const shape = p => p <= 0 ? 0 : p >= 1 ? 1 : (1 - Math.cos(Math.PI * p)) / 2;
if (!reduce) {
  scroll(p => {
    const q = Math.min(1, Math.max(0, (p - 0.08) / 0.72));
    level = D * shape(q);
    rate = q > 0 && q < 1 ? Math.sin(Math.PI * q) : 0;
  }, { target: root });
}
function hud() {
  const mm = level * 1000;
  num.textContent = mm.toFixed(1) + " mm";
  unit.textContent = Math.round(mm) + " litres on one square metre";
}

function size() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  R.setSize(w, h, false); cam.aspect = w / h;
  cam.fov = w < 700 ? 44 : 28;
  // wide screens: the cube sits right of centre, captions own the left
  if (w >= 900) cam.setViewOffset(w, h, -w * 0.13, -h * 0.04, w, h); else cam.clearViewOffset();
  cam.updateProjectionMatrix();
}
addEventListener("resize", size); size();

const M = new THREE.Matrix4(), clock = new THREE.Clock();
let shown = -1;
let frame = function () {
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  // camera: a slow drift around a three-quarter view
  const a = 0.78 + (reduce ? 0 : 0.10 * Math.sin(t * 0.15));
  cam.position.set(Math.sin(a) * 4.9, 2.5, Math.cos(a) * 4.9);
  cam.lookAt(0, 0.42, 0);
  // the storm darkens the room a little, and lifts when it passes
  scene.background.copy(paper).lerp(storm, 0.55 * rate);
  scene.fog.color.copy(scene.background);

  const h = Math.max(level, 0.0008);
  // the body stops just under the surface: two faces at one height
  // z-fight into a camouflage pattern
  const hb = Math.max(h - 0.003, 0.0004);
  body.scale.y = hb; body.position.y = hb / 2; body.visible = level > 0.0005;
  surf.position.y = h; surf.visible = body.visible;
  const pos = surfGeo.attributes.position.array, amp = 0.0009 * (0.3 + rate);
  for (let i = 0; i < pos.length; i += 3) {
    const x = base[i], z = base[i + 2];
    pos[i + 1] = amp * (Math.sin(x * 31 + t * 2.3) * Math.cos(z * 27 - t * 1.9) +
      0.6 * Math.sin((x * 0.7 - z) * 53 + t * 4.1) + 0.35 * Math.cos((x + z * 0.8) * 89 - t * 6.3));
  }
  surfGeo.attributes.position.needsUpdate = true; surfGeo.computeVertexNormals();

  const live = Math.round(N * rate);
  drop.count = live;
  for (let i = 0; i < live; i++) {
    const d = P[i]; d.y -= d.v * dt;
    if (d.y < h) {
      if (Math.random() < 0.25 && RINGS) {
        const r = rings[ri++ % RINGS]; r.position.set(d.x, h + 0.002, d.z); r.userData.t = 0;
      }
      d.y = 1.2 + Math.random() * 2.5; d.x = Math.random() - 0.5; d.z = Math.random() - 0.5;
    }
    M.makeTranslation(d.x * 0.98, d.y, d.z * 0.98); drop.setMatrixAt(i, M);
  }
  drop.instanceMatrix.needsUpdate = true;
  for (const r of rings) {
    if (r.userData.t >= 1) { r.material.opacity = 0; continue; }
    r.userData.t += dt * 2.2;
    const s = 0.004 + r.userData.t * 0.05; r.scale.set(s, 1, s);
    r.material.opacity = 0.6 * (1 - r.userData.t);
  }
  if (Math.abs(shown - level) > 1e-5) { hud(); shown = level; }
  R.render(scene, cam);
  requestAnimationFrame(frame);
};
let onScreen = false, running = false;
new IntersectionObserver(es => { onScreen = es[0].isIntersecting;
  if (onScreen && !running) { running = true; clock.getDelta(); requestAnimationFrame(frame); } }).observe(root);
const _frame = frame;
frame = function () { if (!onScreen) { running = false; return; } _frame(); };
hud(); R.render(scene, cam);
// Captions: each fades in toward the middle of the screen and out before
// it reaches the counter, so prose never passes over a number.
if (!reduce) root.querySelectorAll(".step p").forEach(el => {
  scroll(animate(el, { opacity: [0, 1, 1, 0], transform: ["translateY(24px)", "none", "none", "translateY(-24px)"] },
    { ease: "linear" }), { target: el, offset: ["start end", "center 0.62", "center 0.42", "end 0.25"] });
});
