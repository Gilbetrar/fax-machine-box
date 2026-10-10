// Fax Machine box: 3D model built from data/parts.json.
// World frame is the box frame in mm, Z up. Every part is an extruded
// outline (with holes) in its own local (u, v, w) frame, placed by a 4x4
// row-major transform.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { birchCanvas, loadImage, artUrl, PAD, inkCanvas } from './art2d.js';
export { birchCanvas, loadImage, artUrl, PAD, inkCanvas };

export const INK = '#1d1b19';

// ---------- data helpers (tolerant of small schema differences) ----------
export function partGroup(p) {
  if (p.group) return p.group;
  const s = (p.id + ' ' + (p.name || '')).toLowerCase();
  if (s.includes('drawer') || /^(b|t)_/.test(p.id)) {
    if (s.includes('upper') || s.includes('top drawer') || /^t_/.test(p.id)) return 'drawer_upper';
    return 'drawer_lower';
  }
  if (s.includes('lid')) return 'lid';
  if (s.includes('button')) return 'hardware';
  return 'shell';
}
export const isDrawer = g => g && g.startsWith('drawer');

// Bring any parts.json into the frame the renderer uses: mm, Z up, right-handed,
// +X front to rear, +Y from the right wall to the left wall (seen from the front).
// The geometry exporter writes a left-handed frame (Y left -> right) and says so in
// box.handedness; we reflect Y there, which keeps every face, hole and engraving the
// physical way round (the renderer flips winding for mirrored matrices).
export function normalizeData(d) {
  const B = d.box || {}; const W = B.width || 165.1;
  const flat = t => Array.isArray(t[0]) ? t.flat() : t;
  const left = String(B.handedness || '').toLowerCase().startsWith('l');
  const mir = v => v && [v[0], -v[1], v[2]];
  for (const p of d.parts) {
    p.transform = flat(p.transform);
    if (left) {
      const t = p.transform; // rows 0..3; reflect row 1 (Y) about W/2
      for (let c = 0; c < 4; c++) t[4 + c] = -t[4 + c];
      t[7] += W;
      p.insert_direction = mir(p.insert_direction);
      if (p.art_up) p.art_up = mir(p.art_up);
    }
    p.group = p.group || partGroup(p);
  }
  if (left) for (const s of d.steps || []) s.insert_direction = mir(s.insert_direction);
  if (left && d.hardware && d.hardware.magnets) for (const m of d.hardware.magnets) { m.at = [m.at[0], W - m.at[1], m.at[2]]; m.axis = mir(m.axis); }
  // magnets: derive from the small round holes in the divider and drawer backs when not given
  d.hardware = d.hardware || {};
  if (!d.hardware.magnets) {
    const mags = [];
    for (const p of d.parts) {
      if (!/divider|back/i.test(p.id + ' ' + p.name)) continue;
      const M = new THREE.Matrix4().set(...p.transform);
      for (const h of p.holes || []) {
        if (h.length < 12) continue;
        let cx = 0, cy = 0; for (const [x, y] of h) { cx += x; cy += y; } cx /= h.length; cy /= h.length;
        const r = Math.hypot(h[0][0] - cx, h[0][1] - cy); if (r < 2 || r > 4) continue;
        const at = new THREE.Vector3(cx, cy, p.thickness / 2).applyMatrix4(M);
        const axis = new THREE.Vector3(0, 0, 1).transformDirection(M);
        mags.push({ at: at.toArray(), axis: axis.toArray(), d: 6, h: 2, group: isDrawer(p.group) ? p.group : undefined });
      }
    }
    d.hardware.magnets = mags;
  }
  return d;
}
function sideSign(p) {
  const e = p.exterior_face;
  const s = typeof e === 'string' ? e : (e && (e.side || e.face)) || '+w';
  return /^-|back|bottom|inner|neg/i.test(String(s)) ? -1 : 1;
}
export function stepNumber(s, i) { return s.number ?? s.n ?? s.step ?? s.index ?? (i + 1); }
export function stepParts(s) { return s.parts || s.part_ids || s.added || []; }

function plyEdgeCanvas() {
  const c = document.createElement('canvas'); c.width = 8; c.height = 96;
  const g = c.getContext('2d');
  // 3 plies: light face veneer, darker core, light face veneer, with glue lines
  const bands = [[0, 30, '#e3c89a'], [30, 33, '#6e4b2a'], [33, 63, '#c9a273'], [63, 66, '#6e4b2a'], [66, 96, '#e3c89a']];
  for (const [a, b, col] of bands) { g.fillStyle = col; g.fillRect(0, a, 8, b - a); }
  return c;
}

const texCache = new Map();
function canvasTex(key, make, setup) {
  if (texCache.has(key)) return texCache.get(key);
  const t = new THREE.CanvasTexture(make());
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  setup && setup(t); texCache.set(key, t); return t;
}
export function woodMaterials(thickness) {
  const face = canvasTex('birch', () => birchCanvas(), t => { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1 / 320, 1 / 320); });
  const edge = canvasTex('edge' + thickness, plyEdgeCanvas, t => {
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1 / 50, 1 / thickness); t.offset.set(0, -1 / thickness);
  });
  return [
    new THREE.MeshStandardMaterial({ map: face, roughness: 0.78, metalness: 0, envMapIntensity: 0.6, side: THREE.DoubleSide }),
    new THREE.MeshStandardMaterial({ map: edge, roughness: 0.9, metalness: 0, envMapIntensity: 0.5, side: THREE.DoubleSide }),
  ];
}

// ---------- geometry ----------
function shapeOf(p) {
  const sh = new THREE.Shape(p.outline.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const h of p.holes || []) sh.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
  return sh;
}
const geoCache = new Map();
export function partGeometry(p) {
  const k = p.id + '|' + p.thickness;
  if (!geoCache.has(k)) {
    const g = new THREE.ExtrudeGeometry(shapeOf(p), { depth: p.thickness, bevelEnabled: false, curveSegments: 1, steps: 1 });
    g.computeBoundingBox();
    geoCache.set(k, g);
  }
  return geoCache.get(k);
}
const edgeCache = new Map();
export function partEdges(p) {
  if (!edgeCache.has(p.id)) edgeCache.set(p.id, new THREE.EdgesGeometry(partGeometry(p), 25));
  return edgeCache.get(p.id);
}
const fatCache = new Map();
export function partFatEdges(p) {
  if (!fatCache.has(p.id)) { const g = new LineSegmentsGeometry(); g.setPositions(partEdges(p).attributes.position.array); fatCache.set(p.id, g); }
  return fatCache.get(p.id);
}
export function partMatrix(p) { return new THREE.Matrix4().set(...p.transform); }
export function partCenter(p) {
  const b = partGeometry(p).boundingBox.clone().applyMatrix4(partMatrix(p));
  return b.getCenter(new THREE.Vector3());
}
export function partBox(p) { return partGeometry(p).boundingBox.clone().applyMatrix4(partMatrix(p)); }

// Overlay mesh carrying the engraved art on the part's exterior face.
function nominalCenterLocal(p) {
  if (p.size_mm) return new THREE.Vector2(p.size_mm[0] / 2, p.size_mm[1] / 2);
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const [x, y] of p.outline) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  return new THREE.Vector2((x0 + x1) / 2, (y0 + y1) / 2);
}
// which way is "up" in the art for faces that lie flat (fallback when the manifest says nothing)
const ART_UP = { sliding_lid: [-1, 0, 0], lid: [-1, 0, 0], top_panel: [0, 1, 0] };
export function artFrame(p) {
  const M = partMatrix(p); const sgn = sideSign(p);
  const n = new THREE.Vector3(0, 0, sgn).transformDirection(M);
  let U = p.art_up ? new THREE.Vector3(...p.art_up) : (Math.abs(n.z) > 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(0, 0, 1));
  const d = n.clone().negate();
  const R = new THREE.Vector3().crossVectors(d, U).normalize();
  U = new THREE.Vector3().crossVectors(R, d).normalize();
  const c2 = nominalCenterLocal(p);
  const c = new THREE.Vector3(c2.x, c2.y, sgn > 0 ? p.thickness : 0).applyMatrix4(M);
  return { M, n, U, R, c, sgn };
}
// a2l: optional 2x3 affine mapping art mm (u right, v down, as seen from outside) to
// the part's local outline coords. When given it is exact; otherwise the art is
// projected onto the exterior face using an up vector.
export function artOverlayGeometry(p, sizeMm, texW, texH, a2l) {
  const g = new THREE.ShapeGeometry(shapeOf(p), 1);
  const { M, U, R, c, sgn } = artFrame(p);
  const pos = g.attributes.position; const uv = new Float32Array(pos.count * 2);
  const z = sgn > 0 ? p.thickness + 0.06 : -0.06;
  const v = new THREE.Vector3();
  let inv = null;
  if (a2l) {
    const [[a, b, tx], [cc, d, ty]] = a2l; const det = a * d - b * cc;
    inv = (x, y) => { const X = x - tx, Y = y - ty; return [(d * X - b * Y) / det, (-cc * X + a * Y) / det]; };
  }
  for (let i = 0; i < pos.count; i++) {
    pos.setZ(i, z);
    let s, t;
    if (inv) { const [u, vv] = inv(pos.getX(i), pos.getY(i)); s = u / sizeMm[0]; t = 1 - vv / sizeMm[1]; }
    else { v.set(pos.getX(i), pos.getY(i), z).applyMatrix4(M).sub(c); s = v.dot(R) / sizeMm[0] + 0.5; t = v.dot(U) / sizeMm[1] + 0.5; }
    // account for the transparent padding inside the ink canvas
    s = (s * (texW - 2 * PAD) + PAD) / texW; t = (t * (texH - 2 * PAD) + PAD) / texH;
    uv[2 * i] = s; uv[2 * i + 1] = t;
  }
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  return g;
}

// ---------- the interactive box ----------
export class BoxModel {
  constructor(data) {
    this.data = data; this.root = new THREE.Group();
    this.parts = data.parts; this.byId = Object.fromEntries(data.parts.map(p => [p.id, p]));
    this.units = {}; // id -> {pivot, mesh, part}
    this.groups = { drawer_lower: new THREE.Group(), drawer_upper: new THREE.Group(), lid: new THREE.Group(), shell: new THREE.Group(), hardware: new THREE.Group() };
    for (const g of Object.values(this.groups)) this.root.add(g);
    this.state = { explode: 0, drawer_lower: 0, drawer_upper: 0, lid: 0, button: 0 };
    this.target = { ...this.state };
    const B = data.box || { length: 304.8, width: 165.1, height: 127 };
    this.box = B; this.center = new THREE.Vector3(B.length / 2, B.width / 2, B.height / 2);
    this.art = {}; // face -> overlay mesh
    for (const p of this.parts) this._addPart(p);
    this._addMagnets();
  }
  _addPart(p) {
    const grp = partGroup(p);
    const mats = woodMaterials(p.thickness);
    const mesh = new THREE.Mesh(partGeometry(p), mats.map(m => m.clone()));
    mesh.matrixAutoUpdate = false; mesh.matrix.copy(partMatrix(p));
    mesh.castShadow = true; mesh.receiveShadow = true; mesh.userData.partId = p.id;
    const pivot = new THREE.Group(); pivot.add(mesh);
    let parent = this.groups[grp] || this.groups.shell;
    if (/button/i.test(p.id + p.name)) {
      // rotate about the pivot hole: the button turns down to free the lid
      const M = partMatrix(p); const h = p.holes && p.holes[0];
      let cx = 0, cy = 0; if (h) { for (const [x, y] of h) { cx += x; cy += y; } cx /= h.length; cy /= h.length; }
      const pv = new THREE.Vector3(cx, cy, 0).applyMatrix4(M);
      const axis = new THREE.Vector3(0, 0, 1).transformDirection(M);
      const spin = new THREE.Group(); spin.position.copy(pv); mesh.matrix.premultiply(new THREE.Matrix4().makeTranslation(-pv.x, -pv.y, -pv.z));
      spin.add(mesh); pivot.add(spin); this.button = { spin, axis };
    }
    parent.add(pivot);
    this.units[p.id] = { pivot, mesh, part: p, group: grp, explodeDir: this._explodeDir(p, grp) };
  }
  // Exploded position: every part moves away from the middle of its body (box or
  // drawer) along its own face normal, by an amount that grows with its distance
  // from the middle, so neighbors that share an insert direction still separate.
  _explodeDir(p, grp) {
    const c = partCenter(p);
    let ref = this.center.clone();
    if (isDrawer(grp)) { ref = new THREE.Vector3(); let n = 0; for (const q of this.parts) if (partGroup(q) === grp) { ref.add(partCenter(q)); n++; } ref.divideScalar(n || 1); }
    const d = c.clone().sub(ref);
    const nrm = new THREE.Vector3(0, 0, 1).transformDirection(partMatrix(p));
    const dn = d.dot(nrm);
    let dir, dist;
    if (Math.abs(dn) > 8) { dir = nrm.clone().multiplyScalar(Math.sign(dn)); dist = Math.abs(dn); }
    else if (d.length() > 1) { dir = d.clone().normalize(); dist = d.length(); }
    else { dir = new THREE.Vector3(0, 0, 1); dist = 0; }
    const v = dir.multiplyScalar(isDrawer(grp) ? dist * 0.5 + 22 : dist * 1.15 + 40);
    // the lid also pulls out of the front, so it clears the top panel
    if (grp === 'lid' && p.insert_direction) v.add(new THREE.Vector3(...p.insert_direction).normalize().multiplyScalar(-70));
    return v;
  }
  _addMagnets() {
    const mags = (this.data.hardware && this.data.hardware.magnets) || [];
    const mat = new THREE.MeshStandardMaterial({ color: 0x8d9198, metalness: 0.8, roughness: 0.35 });
    for (const m of mags) {
      const g = new THREE.CylinderGeometry(m.d / 2, m.d / 2, m.h, 24);
      const mesh = new THREE.Mesh(g, mat);
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...m.axis).normalize());
      mesh.position.set(...m.at); mesh.userData.magnet = true;
      (m.group && this.groups[m.group] ? this.groups[m.group] : this.groups.shell).add(mesh);
    }
  }
  async setArt(face, info, variant, mode = 'burn') {
    const pid = info.part_id; const p = this.byId[pid]; if (!p) return;
    if (!p.art_up && (info.up || ART_UP[face])) p.art_up = info.up || ART_UP[face];
    const old = this.art[face]; if (old) { old.parent.remove(old); old.geometry.dispose(); old.material.map && old.material.map.dispose(); old.material.dispose(); delete this.art[face]; }
    if (!variant) return;
    const url = artUrl(variant); if (!url) return;
    const rgb = mode === 'ink' ? [29, 27, 25] : [70, 40, 20];
    const can = await inkCanvas(url, rgb, mode === 'ink' ? 0.95 : 0.85);
    const tex = new THREE.CanvasTexture(can); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    const geo = artOverlayGeometry(p, info.size_mm || p.size_mm, can.width, can.height, info.art_to_local);
    const mat = new THREE.MeshStandardMaterial({ map: tex, transparent: true, depthWrite: false, roughness: 0.95, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
    const m = new THREE.Mesh(geo, mat); m.matrixAutoUpdate = false; m.matrix.copy(partMatrix(p)); m.renderOrder = 2; m.userData.partId = pid;
    this.units[pid].pivot.add(m); this.art[face] = m;
  }
  update(dt) {
    const k = 1 - Math.pow(0.0015, dt); let moving = false;
    for (const key in this.target) {
      const d = this.target[key] - this.state[key];
      if (Math.abs(d) > 1e-4) { this.state[key] += d * k; moving = true; } else this.state[key] = this.target[key];
    }
    this.layout(this.state);
    return moving;
  }
  layout(s) {
    const e = s.explode;
    for (const u of Object.values(this.units)) u.pivot.position.copy(u.explodeDir).multiplyScalar(e);
    this.groups.drawer_lower.position.set(150 * s.drawer_lower + 560 * e, 0, 0);
    this.groups.drawer_upper.position.set(150 * s.drawer_upper + 560 * e, 0, 80 * e);
    this.groups.lid.position.set(-62 * s.lid, 0, 0);
    if (this.button) this.button.spin.setRotationFromAxisAngle(this.button.axis, Math.PI * s.button);
  }
  // world bounding box of the whole model at a given state (default: where it is heading)
  boxAt(st = this.target) {
    this.layout(st); this.root.updateMatrixWorld(true);
    const b = new THREE.Box3().setFromObject(this.root);
    this.layout(this.state); this.root.updateMatrixWorld(true);
    return b;
  }
  groupOffset(g, st = this.target) {
    const e = st.explode;
    if (g === 'drawer_lower') return new THREE.Vector3(150 * st.drawer_lower + 560 * e, 0, 0);
    if (g === 'drawer_upper') return new THREE.Vector3(150 * st.drawer_upper + 560 * e, 0, 80 * e);
    if (g === 'lid') return new THREE.Vector3(-62 * st.lid, 0, 0);
    return new THREE.Vector3();
  }
  toggleDrawer(g) { this.target[g] = this.target[g] > 0.5 ? 0 : 1; }
  toggleLid() {
    const open = this.target.lid < 0.5;
    this.target.lid = open ? 1 : 0;
  }
}

// ---------- viewer ----------
export class Viewer {
  constructor(canvas, model, opts = {}) {
    this.canvas = canvas; this.model = model; this.opts = opts;
    const r = this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    r.outputColorSpace = THREE.SRGBColorSpace; r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 1.05;
    r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
    const sc = this.scene = new THREE.Scene();
    const pm = new THREE.PMREMGenerator(r); sc.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    sc.add(new THREE.HemisphereLight(0xfff6e8, 0xc9b38f, 0.85));
    const fill = new THREE.DirectionalLight(0xfff4e6, 0.7); fill.position.set(model.center.x + 400, model.center.y - 300, 260); sc.add(fill);
    const sun = new THREE.DirectionalLight(0xfff1dc, 1.6); sun.position.set(-160, 120, 700); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); const sca = sun.shadow.camera; sca.left = -800; sca.right = 800; sca.top = 800; sca.bottom = -800; sca.near = 10; sca.far = 1400; sun.shadow.bias = -0.0005; sun.shadow.radius = 6;
    sun.target.position.copy(model.center); sc.add(sun, sun.target);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(3000, 3000), new THREE.ShadowMaterial({ opacity: 0.11 }));
    ground.position.set(model.center.x, model.center.y, -0.2); ground.receiveShadow = true; sc.add(ground);
    sc.add(model.root);
    const cam = this.camera = new THREE.PerspectiveCamera(30, 1, 5, 5000); cam.up.set(0, 0, 1);
    this.home = opts.home || { dir: [-1.0, 0.9, 0.62], dist: 860 };
    this.setView(this.home, false);
    const c = this.controls = new OrbitControls(cam, canvas);
    c.target.copy(model.center); c.enableDamping = true; c.dampingFactor = 0.08; c.minDistance = 220; c.maxDistance = 1800;
    c.maxPolarAngle = Math.PI * 0.62; c.enablePan = false;
    c.autoRotate = !!opts.autoRotate; c.autoRotateSpeed = 0.6;
    // OrbitControls sets touch-action:none, which traps phone users on the canvas; let vertical swipes scroll the page
    canvas.style.touchAction = 'pan-y';
    c.addEventListener('start', () => { c.autoRotate = false; this._fly = null; });
    c.addEventListener('change', () => this.kick());
    this.raycaster = new THREE.Raycaster(); this.selected = null; this.onSelect = opts.onSelect || (() => {});
    this.reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    this._bindPick(); this._resize(); new ResizeObserver(() => { this._resize(); this.kick(); }).observe(canvas);
    this.visible = true;
    new IntersectionObserver(es => { this.visible = es[0].isIntersecting; if (this.visible) this.kick(); }).observe(canvas);
    this._last = performance.now(); this._running = false; this.kick();
  }
  setView(v, animate = true) {
    const dir = new THREE.Vector3(...v.dir).normalize();
    const target = v.target ? new THREE.Vector3(...v.target) : this.model.center.clone();
    const pos = target.clone().add(dir.multiplyScalar(v.dist || 820));
    if (!animate || !this.controls || this.reduced) { this.camera.position.copy(pos); this.camera.lookAt(target); if (this.controls) this.controls.target.copy(target); return; }
    this._fly = { from: this.camera.position.clone(), to: pos, tFrom: this.controls.target.clone(), tTo: target, t: 0 };
    this.controls.autoRotate = false; this.kick();
  }
  // distance at which a box fits the view from direction dir
  fitDistance(box, margin = 1.08) {
    const r = box.getSize(new THREE.Vector3()).length() / 2;
    const fv = THREE.MathUtils.degToRad(this.camera.fov);
    const fh = 2 * Math.atan(Math.tan(fv / 2) * this.camera.aspect);
    return Math.min(4000, Math.max(160, r / Math.sin(Math.min(fv, fh) / 2) * margin));
  }
  // keep the current viewing direction, re-aim at the box and back off until it fits
  fitTo(box, opts = {}) {
    const c = box.getCenter(new THREE.Vector3());
    const dir = opts.dir ? new THREE.Vector3(...opts.dir).normalize() : this.camera.position.clone().sub(this.controls.target).normalize();
    this.setView({ dir: dir.toArray(), target: c.toArray(), dist: this.fitDistance(box, opts.margin || 1.0) }, opts.animate !== false);
  }
  fitModel(opts = {}) { this.fitTo(this.model.boxAt(), opts); }
  snapshot() { this.model.update(10); this.controls.update(); this.renderer.render(this.scene, this.camera); return this.renderer.domElement.toDataURL('image/png'); }
  _resize() {
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight; if (!w || !h) return;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h;
    // keep the whole box in frame on narrow screens
    this.camera.fov = w / h < 1.15 ? 38 : 30; this.camera.updateProjectionMatrix();
  }
  _bindPick() {
    let down = null;
    this.canvas.addEventListener('pointerdown', e => { down = [e.clientX, e.clientY]; });
    this.canvas.addEventListener('pointerup', e => {
      if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 6) return;
      const r = this.canvas.getBoundingClientRect();
      const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      this.raycaster.setFromCamera(ndc, this.camera);
      // nearest visible hit; art overlays carry their part's id, magnets carry none
      const hits = this.raycaster.intersectObjects(this.model.root.children, true)
        .filter(h => h.object.userData.partId && h.object.visible).sort((a, b) => a.distance - b.distance);
      this.select(hits.length ? hits[0].object.userData.partId : null, true);
    });
  }
  select(id, fromClick = false) {
    const prev = this.selected && this.model.units[this.selected];
    if (prev) for (const m of prev.mesh.material) m.emissive.setHex(0x000000);
    this.selected = id;
    const u = id && this.model.units[id];
    if (u) for (const m of u.mesh.material) { m.emissive.setHex(0xf2b33d); m.emissiveIntensity = 0.28; }
    if (u && fromClick) {
      if (isDrawer(u.group)) this.model.toggleDrawer(u.group);
      else if (u.group === 'lid' || /button/i.test(id)) this.model.toggleLid();
    }
    this.onSelect(u ? u.part : null, u ? u.group : null);
    this.kick();
  }
  kick() { if (!this._running) { this._running = true; this._last = performance.now(); requestAnimationFrame(t => this._tick(t)); } }
  _tick(t) {
    const dt = Math.min(0.05, (t - this._last) / 1000); this._last = t;
    let busy = this.model.update(this.reduced ? 10 : dt);
    if (this._fly) {
      const f = this._fly; f.t = Math.min(1, f.t + dt / 0.9); const k = 1 - Math.pow(1 - f.t, 3);
      this.camera.position.lerpVectors(f.from, f.to, k); this.controls.target.lerpVectors(f.tFrom, f.tTo, k);
      if (f.t >= 1) this._fly = null; busy = true;
    }
    const ch = this.controls.update(); busy = busy || ch || this.controls.autoRotate;
    if (this.visible) this.renderer.render(this.scene, this.camera);
    if (busy && this.visible) requestAnimationFrame(tt => this._tick(tt)); else this._running = false;
  }
}

// ---------- still renderer for step pictures, inventory and callouts ----------
export class StillRenderer {
  constructor(data) {
    this.data = data; this.byId = Object.fromEntries(data.parts.map(p => [p.id, p]));
    const canvas = document.createElement('canvas');
    this.r = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    this.r.outputColorSpace = THREE.SRGBColorSpace;
    this.mat = {
      hi: new THREE.MeshLambertMaterial({ color: 0xf2d9a8, polygonOffset: true, polygonOffsetFactor: 3, polygonOffsetUnits: 8 }),
      plain: new THREE.MeshLambertMaterial({ color: 0xfbf7ef, polygonOffset: true, polygonOffsetFactor: 3, polygonOffsetUnits: 8 }),
      ghost: new THREE.MeshLambertMaterial({ color: 0xf1eee8, polygonOffset: true, polygonOffsetFactor: 3, polygonOffsetUnits: 8 }),
      paper: new THREE.MeshLambertMaterial({ color: 0xffffff, polygonOffset: true, polygonOffsetFactor: 3, polygonOffsetUnits: 8 }),
      metal: new THREE.MeshLambertMaterial({ color: 0x9aa0a8 }),
      arrow: new THREE.MeshBasicMaterial({ color: 0xd8423a }),
      hiLine: new LineMaterial({ color: 0x1d1b19, linewidth: 2.6, side: THREE.DoubleSide }),
      ghostLine: new LineMaterial({ color: 0xbdb5a8, linewidth: 2.0, side: THREE.DoubleSide }),
      thinLine: new THREE.LineBasicMaterial({ color: 0x1d1b19 }),
    };
  }
  _scene() {
    const s = new THREE.Scene();
    s.add(new THREE.AmbientLight(0xffffff, 1.9));
    const d = new THREE.DirectionalLight(0xffffff, 1.4); d.position.set(-0.6, -1, 1.6); s.add(d);
    const d2 = new THREE.DirectionalLight(0xffffff, 0.5); d2.position.set(1, 0.4, 0.3); s.add(d2);
    return s;
  }
  addPart(scene, p, style = 'hi', offset = [0, 0, 0], bounds) {
    const g = new THREE.Group(); g.position.set(...offset);
    const m = new THREE.Mesh(partGeometry(p), this.mat[style] || this.mat.hi); m.matrixAutoUpdate = false; m.matrix.copy(partMatrix(p));
    const l = new LineSegments2(partFatEdges(p), style === 'ghost' ? this.mat.ghostLine : this.mat.hiLine); l.matrixAutoUpdate = false; l.matrix.copy(partMatrix(p));
    g.add(m, l); scene.add(g);
    if (bounds) bounds.union(partBox(p).translate(new THREE.Vector3(...offset)));
    return g;
  }
  addBox(scene, center, size, style = 'paper', bounds, quat) {
    const geo = new THREE.BoxGeometry(...size);
    const m = new THREE.Mesh(geo, this.mat[style]); m.position.copy(center); if (quat) m.quaternion.copy(quat);
    const eg = new LineSegmentsGeometry(); eg.setPositions(new THREE.EdgesGeometry(geo).attributes.position.array);
    const l = new LineSegments2(eg, this.mat.hiLine); l.position.copy(center); if (quat) l.quaternion.copy(quat);
    scene.add(m, l); if (bounds) bounds.union(new THREE.Box3().setFromObject(m));
  }
  addMagnet(scene, mg, bounds, offset = [0, 0, 0], style = 'arrow') {
    const geo = new THREE.CylinderGeometry(mg.d / 2 + 0.4, mg.d / 2 + 0.4, mg.h + 0.6, 28);
    const m = new THREE.Mesh(geo, style === 'arrow' ? this.mat.arrow : this.mat.metal);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...mg.axis).normalize());
    m.position.set(mg.at[0] + offset[0], mg.at[1] + offset[1], mg.at[2] + offset[2]); scene.add(m);
    if (bounds) bounds.union(new THREE.Box3().setFromObject(m));
  }
  addArrow(scene, from, dir, len = 55, bounds) {
    const d = new THREE.Vector3(...dir).normalize(); const head = Math.min(18, len * 0.4), rad = Math.max(2.2, len * 0.045);
    const g = new THREE.Group();
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(rad, rad, len - head, 16), this.mat.arrow); shaft.position.y = (len - head) / 2;
    const cone = new THREE.Mesh(new THREE.ConeGeometry(rad * 3, head, 24), this.mat.arrow); cone.position.y = len - head / 2;
    g.add(shaft, cone); g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d); g.position.copy(from); scene.add(g);
    if (bounds) bounds.union(new THREE.Box3().setFromObject(g));
  }
  render(scene, bounds, view, w = 900, h = 640) {
    const dir = new THREE.Vector3(...(view.dir || [-1, -0.9, 0.75])).normalize();
    const up = new THREE.Vector3(...(view.up || [0, 0, 1]));
    const c = bounds.getCenter(new THREE.Vector3());
    const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, -5000, 5000); cam.up.copy(up);
    cam.position.copy(c).add(dir.clone().multiplyScalar(1500)); cam.lookAt(c); cam.updateMatrixWorld();
    // fit the bounds' corners in camera space
    const inv = cam.matrixWorldInverse; let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    for (let i = 0; i < 8; i++) {
      const p = new THREE.Vector3(i & 1 ? bounds.max.x : bounds.min.x, i & 2 ? bounds.max.y : bounds.min.y, i & 4 ? bounds.max.z : bounds.min.z).applyMatrix4(inv);
      x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y);
    }
    const pad = view.pad ?? 1.08; let hw = (x1 - x0) / 2 * pad, hh = (y1 - y0) / 2 * pad; const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    if (hw / hh > w / h) hh = hw * h / w; else hw = hh * w / h;
    cam.left = cx - hw; cam.right = cx + hw; cam.top = cy + hh; cam.bottom = cy - hh; cam.updateProjectionMatrix();
    this.r.setPixelRatio(2); this.r.setSize(w, h, false); this.r.setClearColor(0xffffff, 0);
    for (const m of [this.mat.hiLine, this.mat.ghostLine]) m.resolution.set(w * 2, h * 2);
    // lift outlines toward the camera so they win the depth test against the faces they sit on
    const lift = new THREE.Matrix4().makeTranslation(dir.x * 1.2, dir.y * 1.2, dir.z * 1.2);
    scene.traverse(o => { if (o.isLineSegments2) { if (o.matrixAutoUpdate) o.position.add(dir.clone().multiplyScalar(1.2)); else o.matrix.premultiply(lift); } });
    if (view.clip) {
      const c0 = view.clip.min, c1 = view.clip.max;
      this.r.clippingPlanes = [new THREE.Plane(new THREE.Vector3(1, 0, 0), -c0.x), new THREE.Plane(new THREE.Vector3(-1, 0, 0), c1.x),
        new THREE.Plane(new THREE.Vector3(0, 1, 0), -c0.y), new THREE.Plane(new THREE.Vector3(0, -1, 0), c1.y),
        new THREE.Plane(new THREE.Vector3(0, 0, 1), -c0.z), new THREE.Plane(new THREE.Vector3(0, 0, -1), c1.z)];
    } else this.r.clippingPlanes = [];
    this.r.render(scene, cam);
    const url = this.r.domElement.toDataURL('image/png');
    scene.traverse(o => { if (o.geometry && !geoCache.has(o.geometry) && o.geometry.type !== 'ExtrudeGeometry' && o.geometry.type !== 'EdgesGeometry' && !o.isLineSegments2) o.geometry.dispose(); });
    return url;
  }
}
