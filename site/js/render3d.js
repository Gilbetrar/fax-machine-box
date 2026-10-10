// The 3D layer: hero model, engraving viewer, and the line-art pictures for the
// build guide. Loaded by page.js after everything else is on screen.
import * as THREE from 'three';
import { BoxModel, Viewer, StillRenderer, isDrawer, partBox, partMatrix, artFrame, artUrl, normalizeData } from './box3d.js';
import { stepParts } from './guide.js';
import { V } from './version.js';

const $ = s => document.querySelector(s);
const nextFrame = () => new Promise(r => requestAnimationFrame(() => r()));
const idle = () => new Promise(r => (window.requestIdleCallback || setTimeout)(() => r(), { timeout: 1500 }));
const findPart = (data, re) => data.parts.find(p => re.test(p.id) || re.test(p.name || ''));
const SMALL = () => innerWidth < 760 || (navigator.deviceMemory && navigator.deviceMemory < 4);
// texture URL for a variant: smaller file on phones when the build made one
const texUrl = v => { const p = (SMALL() && v.png_sm) || v.png || v.svg; return artUrl({ png: p }) + '?v=' + V; };

async function applyArt(model, artState, mode) {
  const man = artState.manifest; if (!man) return;
  await Promise.all(Object.entries(man.faces).map(([fid, face]) => {
    const vs = face.variants || []; const v = vs.find(x => x.id === artState.choice[fid]) || vs.find(x => x.default) || vs[0];
    return model.setArt(fid, face, v && { ...v, png: texUrl(v), svg: null }, mode).catch(e => console.warn(e.message));
  }));
}

// ---------- hero ----------
function initHero(ctx, data) {
  const model = new BoxModel(data);
  const card = $('#partcard');
  const qty = {}; for (const p of data.parts) qty[p.letter] = (qty[p.letter] || 0) + 1;
  const viewer = new Viewer($('#hero-canvas'), model, {
    autoRotate: !ctx.reduced && !ctx.prerender,
    onSelect(p, g) {
      if (!p) { card.hidden = true; return; }
      card.hidden = false; $('#pc-letter').textContent = p.letter || '?'; $('#pc-name').textContent = p.name;
      const verb = matchMedia('(pointer: coarse)').matches ? 'Tap' : 'Click';
      $('#pc-hint').textContent = isDrawer(g) ? `${verb} again to slide the drawer` : g === 'lid' ? `${verb} again to slide the lid` : (qty[p.letter] > 1 ? `${qty[p.letter]} in the kit` : '1 in the kit');
    },
  });
  const l = $('#hero-loading'); l && l.remove();
  const fitHome = () => { const f = viewer.fitView(model.cornersAt({ ...model.target, explode: 0, drawer_lower: 0, drawer_upper: 0, lid: 0 }), viewer.home.dir, 1.06); viewer.home.dist = f.dist; viewer.home.target = f.target.toArray(); };
  fitHome(); viewer.setView(viewer.home, false);
  let touched = false; viewer.controls.addEventListener('start', () => { touched = true; });
  // after any state change, fit the model's new bounding box from the current direction
  let fitT = 0; const refit = () => { clearTimeout(fitT); fitT = setTimeout(() => viewer.fitModel({ margin: 1.04 }), 40); };
  new ResizeObserver(() => { fitHome(); if (!touched) viewer.setView(viewer.home, false); else refit(); }).observe($('#hero-canvas'));
  $('#explode').addEventListener('input', e => { model.target.explode = +e.target.value; viewer.kick(); refit(); });
  for (const b of document.querySelectorAll('.controls .chip')) b.addEventListener('click', () => {
    const a = b.dataset.act;
    if (a === 'home') { model.target.explode = 0; $('#explode').value = 0; model.target.drawer_lower = model.target.drawer_upper = model.target.lid = 0; viewer.select(null); fitHome(); viewer.setView(viewer.home); touched = false; }
    else { if (a === 'lid') model.toggleLid(); else model.toggleDrawer(a); refit(); }
    syncChips(); viewer.kick();
  });
  function syncChips() {
    for (const b of document.querySelectorAll('.controls .chip')) {
      const a = b.dataset.act; if (a === 'home') continue;
      b.classList.toggle('on', model.target[a] > 0.5); b.setAttribute('aria-pressed', model.target[a] > 0.5);
    }
  }
  const origSelect = viewer.select.bind(viewer);
  viewer.select = (id, c) => { origSelect(id, c); syncChips(); if (c) refit(); };
  window.faxHero = { model, viewer };
  return { model, viewer };
}

// ---------- engraving viewer ----------
function initEngraving(ctx, data) {
  const st = ctx.artState, man = st.manifest; if (!man) return;
  const model = new BoxModel(data);
  const viewer = new Viewer($('#art-canvas'), model, { home: { dir: [-1, 0.9, 0.6], dist: 760 } });
  window.faxArt = { model, viewer };
  let loaded = false;
  function focusFace(fid) {
    const face = man.faces[fid]; const p = data.parts.find(q => q.id === face.part_id); if (!p) return;
    const g = p.group; const fr = artFrame(p);
    const side = isDrawer(g) && Math.abs(fr.n.y) > 0.9;   // drawer sides only show when the drawer is out
    Object.assign(model.target, { drawer_lower: side && g === 'drawer_lower' ? 1.35 : 0, drawer_upper: side && g === 'drawer_upper' ? 1.35 : 0, lid: 0, explode: 0 });
    const box = partBox(p).translate(model.groupOffset(g));
    // flat faces: look down from the art's bottom edge so the art reads upright on screen
    const flat = Math.abs(fr.n.z) > 0.9;
    let up = fr.U.clone();
    if (face.art_to_local) { const [[, b0], [, d0]] = face.art_to_local; up = new THREE.Vector3(-b0, -d0, 0).transformDirection(partMatrix(p)); }
    const dir = flat ? up.clone().multiplyScalar(-0.55).add(new THREE.Vector3(0, 0, 1)) : fr.n.clone().add(new THREE.Vector3(0, 0, 0.32)).add(fr.R.clone().multiplyScalar(-0.22));
    viewer.fitTo(box, { dir: dir.toArray(), margin: flat ? 1.2 : 1.15 });
  }
  st.listeners.push(async (kind, fid) => {
    if (!loaded) { loaded = true; await applyArt(model, st, st.mode); }
    if (kind === 'face') focusFace(fid);
    else if (kind === 'choice' || kind === 'mode') await applyArt(model, st, st.mode);
    viewer.kick();
  });
  if (st.current) { loaded = true; applyArt(model, st, st.mode).then(() => { focusFace(st.current); viewer.kick(); }); }
}

// ---------- still pictures ----------
function btnDownOf(btn) {
  const M = new THREE.Matrix4().set(...btn.transform); const hh = btn.holes[0]; let cx = 0, cy = 0;
  for (const [x, y] of hh) { cx += x; cy += y; } cx /= hh.length; cy /= hh.length;
  const pv = new THREE.Vector3(cx, cy, 0).applyMatrix4(M); const ax = new THREE.Vector3(0, 0, 1).transformDirection(M);
  const R2 = new THREE.Matrix4().makeTranslation(pv.x, pv.y, pv.z).multiply(new THREE.Matrix4().makeRotationAxis(ax, Math.PI)).multiply(new THREE.Matrix4().makeTranslation(-pv.x, -pv.y, -pv.z));
  return { ...btn, id: btn.id + '_down', transform: Array.from(R2.multiply(M).transpose().elements) };
}
function howPictures(data, R) {
  const B = data.box; const out = {};
  const left = findPart(data, /left wall|^left$/i), lid = findPart(data, /lid/i), btn = findPart(data, /button/i);
  const front = findPart(data, /front wall|^front$/i), bottom = findPart(data, /^bottom$|bottom panel/i), right = findPart(data, /right wall|^right$/i);
  { // paper
    const s = R._scene(), b = new THREE.Box3();
    for (const p of data.parts) {
      if (p === left || p === front || p === btn || isDrawer(p.group)) continue;
      if (p === lid) { R.addPart(s, p, 'ghost', [-60, 0, 0], b); continue; }
      R.addPart(s, p, 'plain', [0, 0, 0], b);
    }
    for (const p of data.parts) if (isDrawer(p.group)) R.addPart(s, p, 'ghost', [0, 0, 0]);
    const floor = (bottom ? partBox(bottom).max.z : 3.2);
    R.addBox(s, new THREE.Vector3(26, B.width / 2, floor + 108 / 2 + 0.2), [26, 139.7, 107.95], 'paper', b);
    for (let i = 1; i < 6; i++) R.addBox(s, new THREE.Vector3(14 + i * 4, B.width / 2, floor + 108 / 2 + 0.2), [0.4, 139.7, 107.95], 'paper');
    out.paper = R.render(s, b, { dir: [-1, 0.75, 0.7] }, 800, 600);
  }
  { // drawers
    const s = R._scene(), b = new THREE.Box3();
    for (const p of data.parts) {
      if (p === right) continue;
      if (p.group === 'drawer_upper') R.addPart(s, p, 'hi', [120, 0, 0], b);
      else if (p.group === 'drawer_lower') R.addPart(s, p, 'hi', [0, 0, 0], b);
      else R.addPart(s, p, 'plain', [0, 0, 0], b);
    }
    for (const m of (data.hardware && data.hardware.magnets) || []) R.addMagnet(s, m, null, m.group === 'drawer_upper' ? [120, 0, 0] : [0, 0, 0]);
    out.drawers = R.render(s, b, { dir: [0.95, -1, 0.7] }, 800, 600);
  }
  if (lid && front) { // lid pulled out
    const s = R._scene(), b = new THREE.Box3();
    for (const p of data.parts) {
      if (isDrawer(p.group)) continue;
      if (p === lid) R.addPart(s, p, 'hi', [-34, 0, 0], b);
      else R.addPart(s, p, 'plain', [0, 0, 0], p === front || p === left ? b : null);
    }
    const lb = partBox(lid).translate(new THREE.Vector3(-34, 0, 0));
    R.addArrow(s, new THREE.Vector3(lb.min.x + 8, (lb.min.y + lb.max.y) / 2, lb.max.z + 16), [-1, 0, 0], 50, b);
    out.lid = R.render(s, b, { dir: [-1, 0.5, 0.45] }, 800, 600);
  }
  if (front && left && bottom) { // exploded corner
    const s = R._scene(); const e = 14;
    R.addPart(s, front, 'hi', [-e, 0, 0]); R.addPart(s, left, 'plain', [0, e, 0]); R.addPart(s, bottom, 'hi', [0, 0, -e]);
    const clip = new THREE.Box3(new THREE.Vector3(-30, B.width - 95, -30), new THREE.Vector3(95, B.width + 30, 80));
    const fit = new THREE.Box3(new THREE.Vector3(-e - 4, B.width - 95, -e - 4), new THREE.Vector3(95, B.width + e + 4, 80));
    out.joints = R.render(s, fit, { dir: [-1, 1.05, 0.8], pad: 1.02, clip }, 800, 600);
  }
  return out;
}
function inventoryPicture(p, R) {
  const s = R._scene(), b = new THREE.Box3();
  R.addPart(s, p, 'hi', [0, 0, 0], b);
  const n = new THREE.Vector3(0, 0, 1).transformDirection(partMatrix(p));
  const flat = Math.abs(n.z) > 0.9;
  const dir = flat ? new THREE.Vector3(-0.35, -0.6, 1) : n.clone().multiplyScalar(-1).add(new THREE.Vector3(0, 0, 0.55)).add(n.clone().cross(new THREE.Vector3(0, 0, 1)).multiplyScalar(0.3));
  return R.render(s, b, { dir: dir.toArray(), up: [0, 0, 1], pad: 1.12 }, 600, 450);
}
function stepCamera(dir) {
  if (!dir) return [-1, 0.9, 0.75];
  const d = new THREE.Vector3(...dir).normalize();
  if (Math.abs(d.z) > 0.7) return [-1, -0.9, -0.8 * Math.sign(d.z)];
  const perp = Math.abs(d.y) > Math.abs(d.x) ? new THREE.Vector3(-0.9, 0, 0) : new THREE.Vector3(0, -0.9, 0);
  return d.clone().negate().add(perp).add(new THREE.Vector3(0, 0, 0.8)).toArray();
}
function stepPicture(step, data, R) {
  const n = step.n ?? 0;
  const by = Object.fromEntries(data.parts.map(p => [p.id, p]));
  let hi = stepParts(step).map(id => by[id]).filter(Boolean);
  const order = p => p.assembly_step ?? 999;
  const s = R._scene(), b = new THREE.Box3();
  const mags = (data.hardware && data.hardware.magnets) || [];
  if (step.focus === 'paper') return null;
  if (step.focus === 'magnets_divider' || step.focus === 'magnets_drawer') {
    const drawer = step.focus === 'magnets_drawer';
    const part = drawer ? data.parts.find(p => p.group === 'drawer_lower' && /back/i.test(p.id + p.name)) : findPart(data, /divider/i);
    if (!part) return null;
    R.addPart(s, part, 'hi', [0, 0, 0], b);
    const pull = drawer ? -1 : 1;   // magnets go into the drawer back from the front, into the divider from the rear
    for (const m of mags) {
      if (drawer ? m.group !== 'drawer_lower' : !!m.group) continue;
      R.addMagnet(s, m, b, [pull * 34, 0, 0]);
      R.addArrow(s, new THREE.Vector3(m.at[0] + pull * 30, m.at[1], m.at[2]), [-pull, 0, 0], 24, b);
    }
    return R.render(s, b, { dir: drawer ? [-0.75, 1, 0.5] : [0.75, -1, 0.5] });
  }
  if (!hi.length) {
    const shell = data.parts.filter(p => !isDrawer(p.group));
    const set = step.focus === 'finished' ? data.parts : step.focus === 'square' ? shell.filter(p => order(p) <= (step.upto || 99)) : shell;
    for (const p of set) {
      let off = [0, 0, 0];
      if (step.focus === 'dryfit' && p.insert_direction) off = p.insert_direction.map(v => -v * 80);
      R.addPart(s, p, step.focus === 'dryfit' ? 'plain' : 'hi', off, b);
    }
    return R.render(s, b, { dir: [-1, 0.9, 0.7] });
  }
  const groups = [...new Set(hi.map(p => p.group))];
  const allDrawer = groups.every(isDrawer);
  const family = allDrawer && step.phase === 'drawer' ? (groups.includes('drawer_lower') ? 'drawer_lower' : groups[0]) : null;
  if (family) hi = hi.filter(p => p.group === family);
  const hiSet = new Set(hi);
  for (const p of data.parts) {
    if (hiSet.has(p) || order(p) >= n) continue;
    if (family && p.group !== family) continue;
    if (!family && isDrawer(p.group) && !allDrawer) continue;
    R.addPart(s, p, 'ghost', [0, 0, 0], b);
  }
  const byDir = new Map(); let small = true;
  for (const p of hi) {
    const dir = step.insert_direction || p.insert_direction;
    const D = family ? 30 : allDrawer ? 120 : 50;
    const off = dir ? dir.map(v => -v * D) : [0, 0, 0];
    const pb = partBox(p); if (pb.getSize(new THREE.Vector3()).length() > 60) small = false;
    R.addPart(s, p, 'hi', off, b);
    if (dir) { const k = dir.join(','); if (!byDir.has(k)) byDir.set(k, { dir, box: new THREE.Box3() }); byDir.get(k).box.union(pb.translate(new THREE.Vector3(...off))); }
  }
  for (const { dir, box } of byDir.values()) {
    const c = box.getCenter(new THREE.Vector3()); const d = new THREE.Vector3(...dir).normalize();
    if (Math.abs(d.z) > 0.7) R.addArrow(s, new THREE.Vector3(box.min.x - 18, c.y, c.z - 26 * d.z), dir, 52, b);
    else if (small) R.addArrow(s, c.clone().sub(d.clone().multiplyScalar(48)), dir, 34, b);
    else R.addArrow(s, new THREE.Vector3(c.x, c.y, box.max.z + 16).sub(d.clone().multiplyScalar(26)), dir, 52, b);
  }
  let fit = b;
  if (small) { fit = new THREE.Box3(); for (const p of hi) fit.union(partBox(p)); fit.expandByScalar(70); }
  const firstDir = byDir.size ? [...byDir.values()][0].dir : null;
  return R.render(s, fit, { dir: stepCamera(firstDir), pad: small ? 1.0 : 1.08 });
}

// pre-render mode: post every picture to the local prerender server
async function save(name, url) {
  const r = await fetch('/__prerender/save?name=' + encodeURIComponent(name), { method: 'POST', body: url });
  if (!r.ok) throw new Error('save ' + name);
}

export async function start(ctx) {
  const data = normalizeData(structuredClone(ctx.data));
  const hero = initHero(ctx, data);
  initEngraving(ctx, data);
  // hero art: defaults only, after the first frame
  const ph = document.querySelector('#hero-stage .hero-ph');
  const heroDone = idle().then(async () => {
    await applyArt(hero.model, ctx.artState, 'burn'); hero.viewer.kick();
    if (ph) setTimeout(() => ph.remove(), 120);
    ctx.artState.listeners.push(async kind => { if (kind === 'choice') { await applyArt(hero.model, ctx.artState, 'burn'); hero.viewer.kick(); } });
    if (ctx.prerender) { await new Promise(r => setTimeout(r, 1500)); await save('hero', hero.viewer.snapshot()); }
  });
  const fresh = ctx.renders && ctx.renders.hash === ctx.dataHash;
  if (fresh && !ctx.prerender) return;           // the pre-rendered pictures already match this data
  await idle();
  const R = new StillRenderer(data); const slots = ctx.slots; const files = {};
  await R.loadArt(ctx.artState.manifest, v => artUrl({ png: v.png_sm || v.png }) + '?v=' + V);
  const put = async (key, url) => { if (!url) return; if (slots[key]) slots[key].set(url); if (ctx.prerender) { await save(key, url); files[key] = `img/render/${key}.png`; } };
  const how = howPictures(data, R);
  for (const [id, url] of Object.entries(how)) await put('how-' + id, url);
  await nextFrame();
  const seen = new Set();
  for (const p of data.parts) { if (seen.has(p.letter)) continue; seen.add(p.letter); await put('inv-' + p.letter, inventoryPicture(p, R)); await nextFrame(); }
  // steps were built from the raw (exporter-frame) data; bring their insert directions into the render frame
  const leftHanded = String((ctx.data.box && ctx.data.box.handedness) || '').startsWith('l');
  for (const s of ctx.steps || []) {
    const sr = leftHanded && s.insert_direction ? { ...s, insert_direction: [s.insert_direction[0], -s.insert_direction[1], s.insert_direction[2]] } : s;
    let url = null; try { url = stepPicture(sr, data, R); } catch (e) { console.warn('step', s.id, e); }
    await put('step-' + s.id, url); await nextFrame();
  }
  if (ctx.prerender) {
    await heroDone;
    files.hero = 'img/render/hero.png';
    await fetch('/__prerender/index', { method: 'POST', body: JSON.stringify({ hash: ctx.dataHash, files }) });
    document.documentElement.dataset.prerendered = '1';
  }
}
