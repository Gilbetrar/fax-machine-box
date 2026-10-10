import * as THREE from 'three';
import {
  BoxModel, Viewer, StillRenderer, partGroup, isDrawer, stepNumber, stepParts,
  partBox, partMatrix, artFrame, inkCanvas, birchCanvas, artUrl, normalizeData,
} from './box3d.js';
import { RULES } from './rules.js';

const $ = (s, el = document) => el.querySelector(s);
const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v; else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null) e.append(k.nodeType ? k : document.createTextNode(String(k)));
  return e;
};
const nextFrame = () => new Promise(r => requestAnimationFrame(() => r()));
async function getJSON(url) {
  try { const r = await fetch(url, { cache: 'no-cache' }); if (!r.ok) return null; return await r.json(); } catch { return null; }
}
const fmtUSD = n => '$' + Number(n).toFixed(2).replace(/\.00$/, '');

// ---------- chrome: nav, title ----------
function initChrome() {
  for (const w of document.querySelectorAll('.rainbow .w')) {
    const t = w.textContent; w.textContent = '';
    for (const ch of t) w.append(h('span', { class: 'ch', 'aria-hidden': 'true' }, ch));
  }
  const nav = $('#nav'), tog = $('#navtoggle');
  tog.addEventListener('click', () => { const o = nav.classList.toggle('open'); tog.setAttribute('aria-expanded', o); });
  nav.addEventListener('click', e => { if (e.target.tagName === 'A') { nav.classList.remove('open'); tog.setAttribute('aria-expanded', false); } });
  const links = [...nav.querySelectorAll('a')];
  const io = new IntersectionObserver(es => {
    for (const e of es) if (e.isIntersecting) for (const a of links) a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id);
  }, { rootMargin: '-45% 0px -50% 0px' });
  for (const a of links) { const s = document.getElementById(a.getAttribute('href').slice(1)); s && io.observe(s); }
  addEventListener('scroll', () => { if (scrollY < 300) for (const a of links) a.classList.remove('on'); }, { passive: true });
}

// ---------- rules ----------
function renderRules() {
  const ol = $('#rules');
  RULES.forEach((r, i) => ol.append(h('li', {},
    h('div', { class: 'rh' }, h('span', { class: 'num' }, i + 1), h('span', {}, r.title)),
    h('div', { html: r.svg }),
    h('p', {}, r.text))));
}

// ---------- art state shared by both viewers ----------
const artState = { manifest: null, choice: {}, mode: 'burn', listeners: [] };
function defaultVariant(face) {
  const vs = face.variants || []; return vs.find(v => v.default) || vs[0];
}
function variantById(fid, vid) { const f = artState.manifest.faces[fid]; return (f.variants || []).find(v => v.id === vid) || defaultVariant(f); }
async function applyArt(model, mode) {
  if (!artState.manifest) return;
  const jobs = [];
  for (const [fid, face] of Object.entries(artState.manifest.faces)) {
    jobs.push(model.setArt(fid, face, variantById(fid, artState.choice[fid]), mode).catch(e => console.warn(e.message)));
  }
  await Promise.all(jobs);
}

// ---------- hero ----------
function initHero(data) {
  const model = new BoxModel(data);
  const card = $('#partcard');
  const qty = {}; for (const p of data.parts) qty[p.letter] = (qty[p.letter] || 0) + 1;
  const viewer = new Viewer($('#hero-canvas'), model, {
    autoRotate: !matchMedia('(prefers-reduced-motion: reduce)').matches,
    onSelect(p, g) {
      if (!p) { card.hidden = true; return; }
      card.hidden = false; $('#pc-letter').textContent = p.letter || '?'; $('#pc-name').textContent = p.name;
      const hint = isDrawer(g) ? 'Tap again to slide the drawer' : (g === 'lid' || /button/i.test(p.id)) ? 'Tap again to slide the lid' : (qty[p.letter] > 1 ? `Part ${p.letter} · ${qty[p.letter]} in the kit` : `Part ${p.letter}`);
      $('#pc-hint').textContent = hint;
    },
  });
  $('#hero-loading').remove();
  $('#explode').addEventListener('input', e => { model.target.explode = +e.target.value; viewer.kick(); });
  for (const b of document.querySelectorAll('.controls .chip')) b.addEventListener('click', () => {
    const a = b.dataset.act;
    if (a === 'home') { model.target.explode = 0; $('#explode').value = 0; model.target.drawer_lower = model.target.drawer_upper = model.target.lid = model.target.button = 0; viewer.select(null); viewer.setView(viewer.home); }
    else if (a === 'lid') model.toggleLid(); else model.toggleDrawer(a);
    syncChips(); viewer.kick();
  });
  function syncChips() {
    for (const b of document.querySelectorAll('.controls .chip')) {
      const a = b.dataset.act; if (a === 'home') continue;
      b.classList.toggle('on', model.target[a] > 0.5); b.setAttribute('aria-pressed', model.target[a] > 0.5);
    }
  }
  const origSelect = viewer.select.bind(viewer);
  viewer.select = (id, c) => { origSelect(id, c); syncChips(); };
  artState.listeners.push(async () => { await applyArt(model, 'burn'); viewer.kick(); });
  window.faxHero = { model, viewer };   // handy for checking views from the console
  return { model, viewer };
}

// ---------- how it works ----------
function findPart(data, re) { return data.parts.find(p => re.test(p.id) || re.test(p.name || '')); }
function shellParts(data) { return data.parts.filter(p => partGroup(p) === 'shell'); }
async function renderHow(data, R) {
  const B = data.box; const grid = $('#how-grid');
  const cards = [
    { id: 'paper', title: 'Paper slot', text: 'The front compartment holds a stack of quarter-letter sheets (4.25 × 5.5 in) standing on their long edge. Slide the lid back to take a page.' },
    { id: 'drawers', title: 'Two drawers with magnet catches', text: 'COLORS holds colored pencils and Lines holds pens. Each drawer pulls out the back. A pair of small magnets, one in the drawer and one in the divider, pulls it shut and keeps it closed when you carry the box.' },
    { id: 'lid', title: 'Sliding lid and turn button', text: 'The lid rides in two slots cut into the side walls. A small wooden turn button bolted to the front wall locks it: turn it up and the lid cannot slide out, turn it down to open.' },
    { id: 'joints', title: 'Finger joints', text: 'Every corner is a row of interlocking fingers cut to the exact plywood thickness. They line the box up square on their own, and a little wood glue makes them permanent.' },
  ];
  const figs = {};
  for (const c of cards) {
    const fig = h('figure', {}, h('span', { class: 'ph' }, 'drawing…'));
    figs[c.id] = fig;
    grid.append(h('article', { class: 'how' }, fig, h('div', { class: 'body' }, h('h3', {}, c.title), h('p', {}, c.text))));
  }
  const put = (id, url, alt) => { figs[id].innerHTML = ''; figs[id].append(h('img', { src: url, alt })); };
  const left = findPart(data, /left wall|^left$/i), lid = findPart(data, /lid/i), btn = findPart(data, /button/i);
  const front = findPart(data, /front wall|^front$/i), bottom = findPart(data, /^bottom$|bottom panel/i), right = findPart(data, /right wall|^right$/i);
  // the turn button, rotated half a turn about its pivot hole (unlocked)
  const btnDown = btn && (() => {
    const M = new THREE.Matrix4().set(...btn.transform); const hh = btn.holes[0]; let cx = 0, cy = 0;
    for (const [x, y] of hh) { cx += x; cy += y; } cx /= hh.length; cy /= hh.length;
    const pv = new THREE.Vector3(cx, cy, 0).applyMatrix4(M); const ax = new THREE.Vector3(0, 0, 1).transformDirection(M);
    const R2 = new THREE.Matrix4().makeTranslation(pv.x, pv.y, pv.z).multiply(new THREE.Matrix4().makeRotationAxis(ax, Math.PI)).multiply(new THREE.Matrix4().makeTranslation(-pv.x, -pv.y, -pv.z));
    const T2 = R2.multiply(M).transpose().elements; return { ...btn, id: btn.id + '_down', transform: Array.from(T2) };
  })();
  // paper
  {
    const s = R._scene(), b = new THREE.Box3();
    for (const p of data.parts) {
      if (p === left || p === front || p === btn || isDrawer(partGroup(p))) continue;
      if (p === lid) { R.addPart(s, p, 'ghost', [-60, 0, 0], b); continue; }
      R.addPart(s, p, 'plain', [0, 0, 0], b);
    }
    for (const p of data.parts) if (isDrawer(partGroup(p))) R.addPart(s, p, 'ghost', [0, 0, 0]);
    // quarter-letter stack, 108 x 140 mm, standing on the long edge
    const floor = (bottom ? partBox(bottom).max.z : 3.2);
    R.addBox(s, new THREE.Vector3(26, B.width / 2, floor + 108 / 2 + 0.2), [26, 139.7, 107.95], 'paper', b);
    for (let i = 1; i < 6; i++) R.addBox(s, new THREE.Vector3(14 + i * 4, B.width / 2, floor + 108 / 2 + 0.2), [0.4, 139.7, 107.95], 'paper');
    put('paper', R.render(s, b, { dir: [-1, 0.75, 0.7] }, 800, 600), 'Cutaway of the front compartment holding a stack of paper on edge');
    await nextFrame();
  }
  // drawers
  {
    const s = R._scene(), b = new THREE.Box3();
    for (const p of data.parts) {
      const g = partGroup(p); if (p === right) continue;
      if (g === 'drawer_upper') R.addPart(s, p, 'hi', [120, 0, 0], b);
      else if (g === 'drawer_lower') R.addPart(s, p, 'hi', [0, 0, 0], b);
      else R.addPart(s, p, 'plain', [0, 0, 0], b);
    }
    for (const m of (data.hardware && data.hardware.magnets) || []) R.addMagnet(s, m, null, m.group === 'drawer_upper' ? [120, 0, 0] : [0, 0, 0]);
    put('drawers', R.render(s, b, { dir: [0.95, -1, 0.7] }, 800, 600), 'The upper drawer pulled out of the back of the box, with its magnet catch');
    await nextFrame();
  }
  // lid + button
  if (lid && front) {
    const s = R._scene(), b = new THREE.Box3();
    for (const p of data.parts) {
      if (isDrawer(partGroup(p))) continue;
      if (p === lid) R.addPart(s, p, 'hi', [-34, 0, 0], b);
      else if (p === btn) R.addPart(s, btnDown, 'hi', [0, 0, 0], b);
      else R.addPart(s, p, 'plain', [0, 0, 0], p === front || p === left ? b : null);
    }
    const lb = partBox(lid).translate(new THREE.Vector3(-34, 0, 0));
    R.addArrow(s, new THREE.Vector3(lb.min.x + 8, (lb.min.y + lb.max.y) / 2, lb.max.z + 16), [-1, 0, 0], 50, b);
    put('lid', R.render(s, b, { dir: [-1, 0.5, 0.3] }, 800, 600), 'The sliding lid pulled forward out of its slots, with the turn button on the front wall');
    await nextFrame();
  }
  // joints: exploded corner
  if (front && left && bottom) {
    const s = R._scene();
    const e = 14;
    R.addPart(s, front, 'hi', [-e, 0, 0]); R.addPart(s, left, 'plain', [0, e, 0]); R.addPart(s, bottom, 'hi', [0, 0, -e]);
    const clip = new THREE.Box3(new THREE.Vector3(-30, B.width - 95, -30), new THREE.Vector3(95, B.width + 30, 80));
    const fit = new THREE.Box3(new THREE.Vector3(-e - 4, B.width - 95, -e - 4), new THREE.Vector3(95, B.width + e + 4, 80));
    put('joints', R.render(s, fit, { dir: [-1, 1.05, 0.8], pad: 1.02, clip }, 800, 600), 'A corner of the box pulled apart to show the interlocking finger joints');
  }
}

// ---------- inventory / hardware / tools ----------
const HW_ICONS = {
  magnet: '<svg viewBox="0 0 54 54"><ellipse cx="27" cy="33" rx="17" ry="7" fill="#9aa0a8" stroke="#1d1b19" stroke-width="2.4"/><path d="M10 25v8M44 25v8" stroke="#1d1b19" stroke-width="2.4"/><ellipse cx="27" cy="25" rx="17" ry="7" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4"/></svg>',
  bolt: '<svg viewBox="0 0 54 54"><path d="M15 12h24c0 7-5 10-12 10s-12-3-12-10z" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4" stroke-linejoin="round"/><path d="M23 22h8v24h-8z" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4"/><path d="M23 27l8 2M23 32l8 2M23 37l8 2M23 42l8 2" stroke="#1d1b19" stroke-width="1.6"/></svg>',
  nut: '<svg viewBox="0 0 54 54"><path d="M27 9l15 9v18l-15 9-15-9V18z" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4" stroke-linejoin="round"/><circle cx="27" cy="27" r="7" fill="#fff" stroke="#1d1b19" stroke-width="2.4"/><circle cx="27" cy="27" r="10.5" fill="none" stroke="#2f6fc9" stroke-width="2"/></svg>',
  washer: '<svg viewBox="0 0 54 54"><circle cx="27" cy="27" r="16" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4"/><circle cx="27" cy="27" r="6" fill="#fff" stroke="#1d1b19" stroke-width="2.4"/></svg>',
};
function hwIcon(name) {
  const n = name.toLowerCase();
  return HW_ICONS[n.includes('magnet') ? 'magnet' : n.includes('nut') ? 'nut' : n.includes('washer') ? 'washer' : 'bolt'];
}
async function renderInventory(data, R) {
  const inv = $('#inventory'); const seen = new Map();
  for (const p of data.parts) { const k = p.letter || p.id; if (!seen.has(k)) seen.set(k, { p, n: 0 }); seen.get(k).n++; }
  const items = [...seen.values()].sort((a, b) => String(a.p.letter).localeCompare(String(b.p.letter)));
  $('#fact-parts') && ($('#fact-parts').textContent = data.parts.length + ' parts');
  const cells = items.map(({ p, n }) => {
    const img = h('img', { alt: p.name, width: 600, height: 450 });
    const sz = p.size_mm ? `${Math.round(p.size_mm[0])} × ${Math.round(p.size_mm[1])} mm` : '';
    const name = n > 1 ? cleanName(p.name) : p.name;
    inv.append(h('div', { class: 'inv' }, h('span', { class: 'letter' }, p.letter), h('span', { class: 'qty' }, '×' + n), img, h('b', {}, name), h('small', {}, sz)));
    return { p, img };
  });
  const hw = $('#hardware');
  let hitems = (data.hardware && data.hardware.items) || [];
  if (!hitems.length) hitems = [
    { name: 'Disc magnet, 6 × 2 mm', qty: 4, spares: 2 }, { name: 'M3 × 14 button-head bolt', qty: 1 },
    { name: 'M3 nyloc nut', qty: 1 }, { name: 'M3 washer', qty: 2 }];
  for (const it of hitems) hw.append(h('div', { class: 'hw', html: hwIcon(it.name) }, h('div', {}, h('b', {}, it.name), it.spares ? h('small', {}, `plus ${it.spares} spares`) : null), h('span', { class: 'qty' }, '×' + it.qty)));
  const tools = new Set(['Calipers (to measure the plywood)', 'Wood glue (PVA)', 'CA glue or epoxy for the magnets', 'Painter\'s tape or clamps', 'Small mallet or a block of wood', '2 mm hex key', '5.5 mm wrench or pliers', '220 grit sandpaper', 'Paste wax', 'Paper cutter or scissors']);
  for (const t of tools) $('#tools').append(h('li', {}, t));
  for (const { p, img } of cells) {
    const s = R._scene(), b = new THREE.Box3();
    R.addPart(s, p, 'hi', [0, 0, 0], b);
    const n = new THREE.Vector3(0, 0, 1).transformDirection(partMatrix(p));
    const flat = Math.abs(n.z) > 0.9;
    const dir = flat ? new THREE.Vector3(-0.35, -0.6, 1) : n.clone().multiplyScalar(-1).add(new THREE.Vector3(0, 0, 0.55)).add(n.clone().cross(new THREE.Vector3(0, 0, 1)).multiplyScalar(0.3));
    img.src = R.render(s, b, { dir: dir.toArray(), up: [0, 0, 1], pad: 1.12 }, 600, 450);
    await nextFrame();
  }
}

// ---------- steps ----------
const SVG_PAPER = `<svg viewBox="0 0 900 640" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="#1d1b19" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" style="filter:url(#wobble)">
<rect x="120" y="70" width="330" height="430" fill="#fff"/><path d="M285 60v450M110 285h350" stroke="#d8423a" stroke-dasharray="18 14"/>
<path d="M300 40l-30 -18M300 40l-30 18" stroke="#d8423a"/><text x="140" y="560" font-family="Kalam, cursive" font-size="40" fill="#1d1b19" stroke="none">letter, 8.5 × 11 in</text>
<path d="M500 285h80m-24-22l24 22-24 22" stroke-width="6"/>
<rect x="630" y="90" width="165" height="215" fill="#fff"/><rect x="645" y="105" width="165" height="215" fill="#fff"/><rect x="660" y="120" width="165" height="215" fill="#fff"/>
<path d="M660 175h165" /><circle cx="800" cy="145" r="15"/>
<text x="610" y="400" font-family="Kalam, cursive" font-size="40" fill="#1d1b19" stroke="none">4 quarters,</text><text x="610" y="448" font-family="Kalam, cursive" font-size="40" fill="#1d1b19" stroke="none">4.25 × 5.5 in</text></g></svg>`;

function stepCamera(dir) {
  if (!dir) return [-1, -0.9, 0.75];
  const d = new THREE.Vector3(...dir).normalize();
  if (Math.abs(d.z) > 0.7) return [-1, -0.9, -0.8 * Math.sign(d.z)];
  const perp = Math.abs(d.y) > Math.abs(d.x) ? new THREE.Vector3(-0.9, 0, 0) : new THREE.Vector3(0, -0.9, 0);
  return d.clone().negate().add(perp).add(new THREE.Vector3(0, 0, 0.8)).toArray();
}
// Site-side wording for the exporter's steps (keyed by step id), plus the steps
// the geometry export does not model: preparation, squaring, magnets, finishing, paper.
const STEP_TEXT = {
  drawer_walls: { title: 'Drawer back and front', note: 'Build two drawers the same way. The back is the panel with the magnet hole; the front has the grip slot.', tools: ['wood glue'] },
  drawer_left_side: { title: 'Drawer left side', tools: ['wood glue'] },
  drawer_right_side: { title: 'Drawer right side', note: 'The four corners close together.', tools: ['wood glue'] },
  drawer_bottom: { title: 'Drawer bottom', note: 'Its edges are plain; the wall tabs go through its hole rows.', tools: ['wood glue'] },
  drawer_face: { title: 'Faceplate', note: 'Put the red-engraved rectangle on the glue side, line up the two grip slots so a finger reaches through both, and clamp. Glue the drawer nowhere else.', tools: ['wood glue', 'clamps'] },
  box_frame: { title: 'Top panel, shelf and divider', note: 'The divider fits one way: the edge with the longer finger run goes to the left wall. If it will not seat, turn it over rather than forcing it.', tools: ['wood glue'] },
  box_right: { title: 'Right wall', note: 'Lid slot mouth to the front.', tools: ['wood glue', 'mallet'] },
  box_rear: { title: 'Rear wall', note: 'Handle it by its edges until it is glued.', tools: ['wood glue', 'mallet'] },
  box_left: { title: 'Left wall', tools: ['wood glue', 'mallet'] },
  box_front: { title: 'Front wall', tools: ['wood glue', 'mallet'] },
  box_bottom: { title: 'Bottom panel', note: 'Its plain edge sits against the rear wall.', tools: ['wood glue', 'mallet'] },
  box_button: { title: 'Turn button', note: 'Stack: bolt, washer, button, wall, washer, nyloc nut. Tighten until the button turns with a firm push. Up locks the lid, down frees it.', hardware: ['M3 × 14 button-head bolt', '2 × M3 washer', 'M3 nyloc nut'], tools: ['2 mm hex key', '5.5 mm wrench'] },
  box_lid: { title: 'Sliding lid', note: 'Slide it over the front wall into both slots until it stops at the divider. Never glue the lid or its slots.' },
  drawers_in: { title: 'Drawers in' },
};
const EXTRA_STEPS = [
  { before: 'drawer_walls', id: 'prep', title: 'Sort the parts and dry-fit', focus: 'dryfit',
    caption: 'Lay the parts out by letter. To tell the side walls apart, count the column of divider holes near the lid slot: the left wall has 8, the right wall has 7. Dry-fit each step before you glue it, and use slow-set wood glue on the finger joints only.',
    tools: ['wood glue (slow-set PVA)', 'clamps or painter\'s tape'] },
  { after: 'box_bottom', id: 'square', title: 'Square and clamp', focus: 'square',
    caption: 'Measure both diagonals. When they match, clamp or tape the box until the glue sets. Wipe squeeze-out inside the drawer bay right away, and try a drawer in each opening to check it slides.',
    tools: ['clamps or painter\'s tape', 'damp cloth'] },
  { after: 'drawers_in', id: 'magnets', title: 'Magnets', focus: 'magnets',
    caption: 'Glue a magnet into each divider hole, flush with its rear face. Then hold each drawer fully shut, check which way its magnet is pulled, and glue it into the hole in the drawer back, flush with the face that touches the divider.',
    hardware: ['4 × 6 × 2 mm disc magnet'], tools: ['CA glue or epoxy'] },
  { after: 'magnets', id: 'finishing', title: 'Finishing', focus: 'finished',
    caption: 'Sand scorched edges lightly with 220 grit and wipe off the dust. Rub paste wax on the drawer runners and the lid edges so they glide. An oil finish on the outside is optional; keep it off glued faces.',
    tools: ['220 grit sandpaper', 'cloth', 'paste wax'] },
  { after: 'finishing', id: 'paper', title: 'Paper', focus: 'paper',
    caption: 'Cut letter paper into quarters, 4.25 × 5.5 in. Stand a stack on its long edge in the front compartment.',
    hardware: ['letter paper'], tools: ['paper cutter or scissors'] },
];
function buildSteps(data) {
  const out = (data.steps || []).map((s, i) => {
    const t = STEP_TEXT[s.id] || {};
    const base = s.caption || s.text || s.description || '';
    return { ...s, n: stepNumber(s, i), title: s.title || t.title || base.split(/[.:]/)[0], caption: [base, t.note].filter(Boolean).join(' '),
      hardware: s.hardware || t.hardware || [], tools: s.tools || t.tools || [] };
  });
  for (const x of EXTRA_STEPS) {
    if (out.some(s => s.id === x.id)) continue;
    let at = out.length;
    if (x.before) { const k = out.findIndex(s => s.id === x.before); if (k >= 0) at = k; }
    if (x.after) { const k = out.findIndex(s => s.id === x.after); if (k >= 0) at = k + 1; }
    out.splice(at, 0, { ...x, parts: [], extra: true });
  }
  return out;
}
function renderStep(step, idx, data, R) {
  const n = step.n ?? idx + 1;
  const by = Object.fromEntries(data.parts.map(p => [p.id, p]));
  let hi = stepParts(step).map(id => by[id]).filter(Boolean);
  const order = p => p.assembly_step ?? 999;
  const s = R._scene(), b = new THREE.Box3();
  const mags = (data.hardware && data.hardware.magnets) || [];
  if (step.focus === 'paper') return { svg: SVG_PAPER };
  if (step.focus === 'magnets') {
    const div = findPart(data, /divider/i); const back = data.parts.find(p => p.group === 'drawer_lower' && /back/i.test(p.id + p.name));
    if (div) R.addPart(s, div, 'ghost', [0, 0, 0], b);
    const dOff = [60, 0, 0];
    if (back) R.addPart(s, back, 'ghost', dOff, b);
    for (const m of mags) {
      if (m.group && m.group !== 'drawer_lower') continue;
      R.addMagnet(s, m, b, m.group ? dOff : [0, 0, 0]);
    }
    return { url: R.render(s, b, { dir: [1, -1, 0.55] }) };
  }
  if (!hi.length) {
    const shell = data.parts.filter(p => !isDrawer(p.group));
    for (const p of step.focus === 'finished' ? data.parts : shell) {
      let off = [0, 0, 0];
      if (step.focus === 'dryfit' && p.insert_direction) off = p.insert_direction.map(v => -v * 80);
      R.addPart(s, p, step.focus === 'dryfit' ? 'plain' : 'hi', off, b);
    }
    return { url: R.render(s, b, { dir: [-1, 0.9, 0.7] }), glue: step.focus === 'square' };
  }
  const groups = [...new Set(hi.map(p => p.group))];
  const allDrawer = groups.every(isDrawer);
  // building a drawer: show the lower one only (both are made the same way)
  const family = allDrawer && step.phase === 'drawer' ? (groups.includes('drawer_lower') ? 'drawer_lower' : groups[0]) : null;
  if (family) hi = hi.filter(p => p.group === family);
  const hiSet = new Set(hi);
  for (const p of data.parts) {
    if (hiSet.has(p) || order(p) >= n) continue;
    if (family && p.group !== family) continue;
    if (!family && isDrawer(p.group) && !allDrawer) continue;   // drawers are built separately, they go in last
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
  return { url: R.render(s, fit, { dir: stepCamera(firstDir), pad: small ? 1.0 : 1.08 }) };
}
async function renderSteps(data, R) {
  const steps = buildSteps(data); const list = $('#steps'); const nav = $('#stepnav');
  const by = Object.fromEntries(data.parts.map(p => [p.id, p]));
  const pics = [];
  steps.forEach((s, i) => {
    const num = i + 1;
    const letters = new Map();
    let ids = stepParts(s);
    if (s.phase === 'drawer') ids = ids.filter(id => !/^t_/i.test(id));
    for (const id of ids) { const p = by[id]; if (p && !letters.has(p.letter)) letters.set(p.letter, p); }
    const pic = h('div', { class: 'step-pic' }, h('span', { class: 'ph' }, 'drawing step ' + num + '…'));
    const chips = h('div', { class: 'step-parts' },
      [...letters.values()].slice(0, 8).map(p => h('span', { class: 'pchip' }, h('span', { class: 'letter' }, p.letter), cleanName(p.name))),
      s.phase === 'drawer' ? h('span', { class: 'pchip tool' }, '× 2 drawers') : null,
      (s.hardware || []).map(x => h('span', { class: 'pchip hwc' }, x)),
      (s.tools || []).map(x => h('span', { class: 'pchip tool' }, x)));
    const li = h('li', { class: 'step', id: 'step-' + num },
      h('div', { class: 'step-head' }, h('span', { class: 'step-n' }, num), h('h3', {}, s.title || '')),
      pic, chips, s.caption ? h('p', {}, s.caption) : null);
    list.append(li); pics.push({ s, i, num, pic });
    nav.append(h('a', { href: '#step-' + num }, num));
  });
  for (const { s, i, num, pic } of pics) {
    let r = null;
    try { r = renderStep(s, i, data, R); } catch (e) { console.warn('step', i, e); }
    pic.innerHTML = '';
    if (r && r.svg) pic.innerHTML = r.svg;
    else if (r && r.url) pic.append(h('img', { src: r.url, alt: 'Step ' + num + ': ' + (s.title || '') }));
    if (r && r.glue) pic.append(h('span', { class: 'glue-flag' }, 'clamp'));
    await nextFrame();
  }
}
const cleanName = n => n.replace(/\s*\((lower|upper)( drawer)?\)/i, '');

// ---------- engraving ----------
function faceLabel(fid, face, data) {
  const p = data.parts.find(q => q.id === face.part_id);
  const nice = { left_wall: 'Left wall', right_wall: 'Right wall', front_wall: 'Front', top_panel: 'Top', sliding_lid: 'Lid', faceplate_colors: 'COLORS drawer', faceplate_lines: 'Lines drawer' };
  if (nice[fid]) return nice[fid];
  const m = fid.match(/drawer_side_(\d)/); if (m) return 'Drawer side ' + m[1];
  return p ? p.name : fid.replace(/_/g, ' ');
}
async function burnPreview(url, w) {
  const ink = await inkCanvas(url, [70, 40, 20], 0.86);
  const c = document.createElement('canvas'); const s = w / ink.width; c.width = w; c.height = Math.round(ink.height * s);
  const g = c.getContext('2d');
  g.drawImage(birchCanvas(1024, 512, 11), 0, 0, c.width, c.height);
  g.filter = 'blur(0.6px)'; g.drawImage(ink, 0, 0, c.width, c.height); g.filter = 'none';
  return c;
}
function initEngraving(data) {
  const man = artState.manifest; if (!man || !Object.keys(man.faces || {}).length) { $('#variants').append(h('div', { class: 'soon' }, h('div', {}, h('b', {}, 'Art coming soon'), h('span', {}, 'The engraving files are still being drawn.')))); return; }
  const model = new BoxModel(data);
  const viewer = new Viewer($('#art-canvas'), model, { home: { dir: [-1, -0.9, 0.6], dist: 760 } });
  viewer.onSelect = () => {};
  const tabs = $('#facetabs'), vbox = $('#variants');
  const faces = Object.entries(man.faces);
  let current = faces[0][0];
  function focusFace(fid) {
    const face = man.faces[fid]; const p = data.parts.find(q => q.id === face.part_id); if (!p) return;
    const g = partGroup(p);
    const fr = artFrame(p);
    const side = isDrawer(g) && Math.abs(fr.n.y) > 0.9;   // drawer sides only show when the drawer is out
    const OPEN = 1.35;
    model.target.drawer_lower = side && g === 'drawer_lower' ? OPEN : 0; model.target.drawer_upper = side && g === 'drawer_upper' ? OPEN : 0;
    model.target.lid = 0; model.target.button = 0; model.target.explode = 0;
    const c = fr.c.clone(); if (side) c.x += 150 * OPEN;
    const size = Math.max(...(face.size_mm || p.size_mm || [200, 100]));
    let dir, dist;
    if (Math.abs(fr.n.z) > 0.9) { dir = new THREE.Vector3(-0.45, -0.75, 1.5); dist = size * 2.3 + 160; }
    else { dir = fr.n.clone().add(new THREE.Vector3(0, 0, 0.32)).add(fr.R.clone().multiplyScalar(-0.22)); dist = size * 1.6 + 120; }
    viewer.setView({ dir: dir.toArray(), target: c.toArray(), dist });
  }
  async function showFace(fid) {
    current = fid;
    for (const b of tabs.children) b.setAttribute('aria-selected', b.dataset.face === fid);
    const face = man.faces[fid]; vbox.innerHTML = '';
    const chosen = variantById(fid, artState.choice[fid]);
    for (const v of face.variants || []) {
      const url = artUrl(v);
      const inkImg = h('img', { src: url, alt: v.label + ' line art', loading: 'lazy' });
      const burnSlot = h('div', {});
      const btn = h('button', { class: 'var' + (v === chosen ? ' on' : ''), 'aria-pressed': v === chosen },
        h('div', { class: 'pair' }, inkImg, burnSlot),
        h('div', { class: 'lbls' }, h('span', {}, 'line art'), h('span', {}, 'burned on birch')),
        h('div', { class: 'cap' }, h('div', {}, h('b', {}, v.label || v.id), v.notes ? h('small', {}, ' ' + v.notes) : null), v === chosen ? h('span', { class: 'tag' }, 'on the box') : null));
      btn.addEventListener('click', async () => {
        artState.choice[fid] = v.id; showFace(fid);
        for (const f of artState.listeners) f();
      });
      vbox.append(btn);
      burnPreview(url, 700).then(c => burnSlot.append(c)).catch(e => console.warn(e.message));
    }
    focusFace(fid);
  }
  for (const [fid, face] of faces) tabs.append(h('button', { role: 'tab', 'data-face': fid, onclick: () => showFace(fid) }, faceLabel(fid, face, data)));
  for (const b of document.querySelectorAll('.segbtn')) b.addEventListener('click', async () => {
    artState.mode = b.dataset.mode; for (const x of document.querySelectorAll('.segbtn')) x.classList.toggle('on', x === b);
    await applyArt(model, artState.mode); viewer.kick();
  });
  artState.listeners.push(async () => { await applyArt(model, artState.mode); viewer.kick(); });
  // start rendering only when the section is near
  const io = new IntersectionObserver(async es => {
    if (!es[0].isIntersecting) return; io.disconnect();
    await applyArt(model, artState.mode); showFace(current); viewer.kick();
  }, { rootMargin: '400px' });
  io.observe($('#engraving'));
}

// ---------- downloads ----------
const THICKS = Array.from({ length: 8 }, (_, i) => (2.8 + i * 0.1).toFixed(1));
// downloads/manifest.json: { thicknesses: { "3.2": { folder, zip, files: [...], sheets: { bed: n } } },
//                           beds: { bed: { width_mm, height_mm, sheets_by_thickness } } }
// Older/looser shapes (arrays, {zip, svg, dxf} objects) are accepted too.
function normThicknesses(m) {
  const out = {}; const src = m.thicknesses || m.by_thickness || {};
  const add = (t, f) => { if (f && !isNaN(+t)) out[Number(t).toFixed(1)] = f; };
  if (Array.isArray(src)) for (const e of src) add(e.thickness ?? e.mm ?? e.t, e);
  else for (const [t, f] of Object.entries(src)) add(t, f);
  return out;
}
const BED_NAMES = { ponoko: 'Ponoko', xtool_s1: 'xTool S1', xtool_p2: 'xTool P2', glowforge_pro: 'Glowforge Pro', generic_600x400: 'Any 600 × 400 mm bed', nycr: 'NYC Resistor (Epilog 32 × 20 in)' };
function normBeds(m, t, entry) {
  const src = m.beds || m.layouts || {}; const out = [];
  const list = Array.isArray(src) ? src.map(b => [b.id || b.name, b]) : Object.entries(src);
  for (const [id, v] of list) {
    const o = typeof v === 'object' ? v : { sheets: v };
    const sheets = (entry && entry.sheets && entry.sheets[id]) ?? (o.sheets_by_thickness && o.sheets_by_thickness[t]) ?? o.sheets ?? o.sheet_count;
    out.push({ id, name: o.name || o.label || BED_NAMES[id] || id.replace(/_/g, ' '), size: o.width_mm ? `${Math.round(o.width_mm)} × ${Math.round(o.height_mm)} mm` : (o.size || ''), sheets, files: o.files });
  }
  return out;
}
const fileUrl = (base, folder, f) => /^(https?:|\/)/.test(f) ? f : base + (folder && !f.includes('/') ? folder + '/' : '') + f;
function entryFiles(entry) { return Array.isArray(entry.files) ? entry.files : []; }
function dlBtn(href, label, cls = 'btn-line') { return h('a', { class: 'btn ' + cls, href, download: '' }, label); }
const soonBox = (title, text) => h('div', { class: 'soon', html: '<svg width="44" height="44" viewBox="0 0 44 44"><rect x="6" y="4" width="28" height="36" rx="3" fill="#fff" stroke="#1d1b19" stroke-width="2.4"/><path d="M12 14h16M12 20h16M12 26h10" stroke="#1d1b19" stroke-width="2.2" stroke-linecap="round"/><circle cx="33" cy="33" r="8" fill="#f6d33c" stroke="#1d1b19" stroke-width="2.4"/><path d="M33 29v4l3 2" stroke="#1d1b19" stroke-width="2.2" stroke-linecap="round"/></svg>' }, h('div', {}, h('b', {}, title), h('span', {}, text)));
async function initFiles() {
  const base = 'downloads/'; let man = await getJSON(base + 'manifest.json');
  const byT = man ? normThicknesses(man) : {};
  if (man && (man.status === 'pending' || !Object.keys(byT).length)) man = null;
  const thick = $('#thick'); let sel = '3.2';
  function render() {
    for (const b of thick.children) b.setAttribute('aria-checked', b.dataset.t === sel);
    $('#thick-read').textContent = `${sel} mm is about ${(sel / 25.4).toFixed(3)} in.`;
    const box = $('#box-dl'), coupon = $('#coupon-dl'), bedsEl = $('#beds');
    box.innerHTML = ''; coupon.innerHTML = ''; bedsEl.innerHTML = '';
    if (!man) {
      box.append(soonBox('Files coming soon', 'The cut files for every thickness are being regenerated. This page will offer a zip, SVG and DXF for each one.'));
      coupon.append(soonBox('Coupon file coming soon', 'It ships with the box files.'));
      return;
    }
    const e = byT[sel];
    if (!e) { box.append(soonBox(`No files for ${sel} mm yet`, 'Pick another thickness, or generate your own from the source.')); return; }
    const files = entryFiles(e), folder = e.folder || '';
    // coupon
    const cps = files.filter(f => /coupon/i.test(f));
    if (cps.length) coupon.append(h('div', { class: 'dl-row' }, cps.map(f => dlBtn(fileUrl(base, folder, f), (/\.dxf$/i.test(f) ? 'Coupon DXF' : 'Coupon SVG') + ` · ${sel} mm`))));
    else coupon.append(soonBox('Coupon file coming soon', 'It ships with the box files.'));
    // whole set
    box.append(h('p', {}, `Every part for ${sel} mm plywood, laid out on sheets for each laser bed below and color-coded for cutting. The zip holds all of them plus the coupon.`));
    const row = h('div', { class: 'dl-row' });
    if (e.zip) row.append(dlBtn(fileUrl(base, '', e.zip), `Download all (.zip, ${sel} mm)`, 'btn-ink'));
    box.append(row);
    // layouts per bed
    const beds = normBeds(man, sel, e);
    if (beds.length) {
      bedsEl.append(h('h4', { class: 'bedh' }, 'Sheet layouts by laser bed'));
      const g = h('div', { class: 'beds' });
      for (const b of beds) {
        const sheetFiles = files.filter(f => f.startsWith(b.id + '_sheet_'));
        const nums = [...new Set(sheetFiles.map(f => +f.match(/_sheet_(\d+)/)[1]))].sort((x, y) => x - y);
        g.append(h('div', { class: 'bed' },
          h('b', {}, b.name),
          h('small', {}, [b.size, b.sheets != null ? `${b.sheets} sheet${b.sheets == 1 ? '' : 's'}` : null].filter(Boolean).join(' · ')),
          h('ul', { class: 'sheets' }, nums.map(k => h('li', {}, h('span', {}, 'Sheet ' + k),
            sheetFiles.filter(f => +f.match(/_sheet_(\d+)/)[1] === k).sort().reverse().map(f => h('a', { href: fileUrl(base, folder, f), download: '' }, f.split('.').pop().toUpperCase())))))));
      }
      bedsEl.append(g);
    }
  }
  for (const t of THICKS) thick.append(h('button', { role: 'radio', 'data-t': t, onclick: () => { sel = t; render(); } }, t));
  render();
}

// ---------- materials + drawing kit ----------
async function initMaterials() {
  const d = await getJSON('data/materials.json'); const kit = await getJSON('data/drawing-kit.json');
  const el = $('#materials-list');
  if (!d || !d.items) { el.append(soonBox('List coming soon', 'Exact product links are being checked.')); return; }
  if (d.checked) $('#mat-intro').textContent = `Everything besides the laser cutting. Links go to the listings we checked (${new Date(d.checked + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}); prices move, so treat them as a guide.`;
  let items = d.items;
  items = items.filter(i => !(i.category === 'Game supplies' && /\b(pens?|pencils?)\b/i.test(i.name)));
  const cats = [...new Set(items.map(i => i.category))];
  for (const c of cats) {
    const list = h('div', { class: 'mlist' });
    for (const i of items.filter(x => x.category === c)) {
      const pending = !i.url && i.price_usd == null;
      list.append(h('div', { class: 'mitem' + (pending ? ' pending' : '') },
        h('div', { class: 'top' }, h('b', {}, i.name), i.price_usd != null ? h('span', { class: 'price' }, fmtUSD(i.price_usd)) : null),
        i.spec ? h('span', { class: 'spec' }, i.spec) : null,
        i.note ? h('p', { class: 'note' }, i.note) : null,
        h('div', { class: 'foot2' }, h('span', { class: 'qty' }, pending ? 'Recommendations coming soon' : (i.qty ? `Need: ${i.qty}` : '')), i.url ? h('a', { class: 'buy', href: i.url, target: '_blank', rel: 'noopener' }, 'View listing') : null)));
    }
    el.append(h('div', { class: 'mcat' }, h('h3', {}, c), list));
  }
  await renderCatalog(kit);
}

// Drawing catalog: mix-and-match products by category. Reads data/drawing-catalog.json;
// until that exists, builds the same shape from drawing-kit.json's tier items.
const CAT_FROM_ROLE = { color: ['colored-pencils', 'Colored pencils'], line: ['line-pens', 'Line pens'], brush: ['brush-pens', 'Brush pens & markers'], marker: ['brush-pens', 'Brush pens & markers'], graphite: ['graphite', 'Graphite pencils'], sharpener: ['sharpeners', 'Sharpeners'], eraser: ['erasers', 'Erasers'] };
function catalogFromKit(kit) {
  const cats = new Map(); const seen = new Set();
  for (const t of kit.tiers || []) for (const i of t.items || []) {
    if (seen.has(i.name)) continue; seen.add(i.name);
    const [id, name] = CAT_FROM_ROLE[i.role] || [i.role, i.role];
    if (!cats.has(id)) cats.set(id, { id, name, items: [] });
    cats.get(id).items.push({ name: i.name, pack: '', price_usd: i.price_usd, url: i.url, good_for: i.why, favorite: /favorite/i.test(i.why || ''), ben_uses: false });
  }
  const order = ['colored-pencils', 'line-pens', 'brush-pens', 'graphite', 'sharpeners', 'erasers'];
  return { checked: kit.checked, categories: [...cats.values()].sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id)) };
}
const PRODUCT_ICON = '<svg viewBox="0 0 80 60" aria-hidden="true"><g fill="none" stroke="#1d1b19" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M10 44 L56 14 L66 22 L20 52 Z" fill="#f6d33c"/><path d="M56 14 L66 22 L72 12 Z" fill="#ecd6ae"/><path d="M20 52 L10 44 L8 54 Z" fill="#fff"/></g></svg>';
function productImg(i) {
  const f = i.image_file || (i.asin ? i.asin + '.jpg' : null);
  if (f) return h('img', { src: 'img/products/' + f.split('/').pop(), alt: '', loading: 'lazy', width: 160, height: 160 });
  return h('span', { class: 'noimg', html: PRODUCT_ICON });
}
async function renderCatalog(kit) {
  const el = $('#kit-tiers'); el.innerHTML = '';
  let cat = await getJSON('data/drawing-catalog.json');
  if (cat && !cat.categories) cat = null;
  if (!cat && kit && kit.tiers) cat = catalogFromKit(kit);
  if (!cat || !cat.categories) { el.append(soonBox('Drawing kit: pens and pencils', 'Recommendations are coming soon.')); return; }
  const when = cat.checked ? new Date(cat.checked + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : null;
  $('#kit-intro').textContent = 'Mix and match: everything here fits the COLORS and Lines drawers.' + (when ? ` Prices checked ${when}.` : '');
  for (const c of cat.categories) {
    const grid = h('div', { class: 'cgrid' });
    for (const i of c.items || []) {
      grid.append(h('article', { class: 'prod' + (i.favorite ? ' fav' : '') },
        h('div', { class: 'pimg' }, productImg(i),
          i.favorite ? h('span', { class: 'badge fav' }, "Ben's favorite") : i.ben_uses ? h('span', { class: 'badge uses' }, 'Ben uses this') : null),
        h('div', { class: 'pbody' },
          h('b', {}, i.name),
          h('span', { class: 'pack' }, [i.pack, i.price_usd != null ? fmtUSD(i.price_usd) : null].filter(Boolean).join(' · ')),
          i.good_for ? h('p', {}, i.good_for) : null,
          i.url ? h('a', { class: 'buy', href: i.url, target: '_blank', rel: 'noopener' }, 'View on Amazon') : null)));
    }
    el.append(h('section', { class: 'ccat' }, h('div', { class: 'ccat-head' }, h('h4', {}, c.name), c.blurb ? h('p', {}, c.blurb) : null), grid));
  }
}

// ---------- cutting options ----------
const ICON = {
  cloud: '<svg class="icon" viewBox="0 0 52 52"><path d="M14 38h26a9 9 0 0 0 0-18 13 13 0 0 0-25-2 10 10 0 0 0-1 20z" fill="#fff" stroke="#1d1b19" stroke-width="2.6" stroke-linejoin="round"/><path d="M26 24v12m-6-6 6 6 6-6" stroke="#2f6fc9" stroke-width="2.6" fill="none" stroke-linecap="round"/></svg>',
  space: '<svg class="icon" viewBox="0 0 52 52"><rect x="6" y="14" width="40" height="26" rx="4" fill="#f6d33c" stroke="#1d1b19" stroke-width="2.6"/><path d="M12 14V9h28v5M14 26h24" stroke="#1d1b19" stroke-width="2.6" fill="none"/><circle cx="38" cy="33" r="3" fill="#d8423a"/></svg>',
  shop: '<svg class="icon" viewBox="0 0 52 52"><path d="M8 20h36v22H8z" fill="#fff" stroke="#1d1b19" stroke-width="2.6"/><path d="M6 20l5-10h30l5 10" fill="#3f9b4b" stroke="#1d1b19" stroke-width="2.6" stroke-linejoin="round"/><rect x="21" y="28" width="10" height="14" fill="#f6d33c" stroke="#1d1b19" stroke-width="2.4"/></svg>',
  laser: '<svg class="icon" viewBox="0 0 52 52"><rect x="5" y="16" width="42" height="24" rx="3" fill="#fff" stroke="#1d1b19" stroke-width="2.6"/><path d="M5 24h42" stroke="#1d1b19" stroke-width="2.4"/><path d="M26 6v14" stroke="#d8423a" stroke-width="3" stroke-linecap="round"/><circle cx="26" cy="22" r="2.5" fill="#d8423a"/></svg>',
};
function initOptions() {
  const opts = [
    { icon: 'space', title: 'A makerspace laser', cost: '~$45–105', sub: 'machine time per box, plus a one-time class', rec: true,
      pts: ['NYC Resistor (Boerum Hill): $1 per minute self-serve after an $85 class; Epilog 60 W, 32 × 20 in bed', 'Engraves and cuts in one or two craft nights', 'Bring your own plywood (about $30)'] },
    { icon: 'cloud', title: 'Online cutting service', cost: '~$150–200', sub: 'cut only, plus shipping',
      pts: ['SendCutSend: instant guest quote about $195 for 1/8 in Baltic birch; DXF files; no wood engraving', 'Ponoko: about $153 cut-only; engraving priced by machine time (adds roughly $60–200)', 'Easiest if you skip the art'] },
    { icon: 'shop', title: 'A local laser shop', cost: '$200+', sub: 'minimum order',
      pts: ['Fabberz (Industry City): $200 minimum, per-minute pricing', 'DIVISION and PrintAWorld quote by file', 'Good if you want someone else to run the machine'] },
    { icon: 'laser', title: 'Your own laser', cost: '$1,700+', sub: 'one-time, for many boxes',
      pts: ['xTool S1 diode (498 × 319 mm bed) from $1,699; about 2 to 5 hours per box', 'xTool P2S 55 W CO2 from $2,999; under 2 hours', 'Needs real ventilation: birch plywood smoke is harsh'] },
  ];
  const el = $('#options');
  for (const o of opts) el.append(h('article', { class: 'opt' + (o.rec ? ' rec' : ''), html: ICON[o.icon] }, o.rec ? h('span', { class: 'badge' }, 'recommended') : null, h('h3', {}, o.title), h('div', { class: 'cost' }, o.cost, h('small', {}, o.sub)), h('ul', {}, o.pts.map(p => h('li', {}, p)))));
}

function initParams(data) {
  const T = data.box && data.box.thickness;
  const rows = [
    ['thickness', `Plywood thickness. Default ${T ? T.toFixed(3) : '3.175'} mm (1/8 in); files are generated from 2.8 to 3.5 mm.`],
    ['burn', 'Half the laser kerf, added back to every edge. About 0.08–0.10 mm for a CO2 laser on birch.'],
    ['finger play', 'Extra gap in each finger slot so joints close without forcing. 0.1 mm.'],
    ['slide clearance', 'Play around the drawers and the lid. 1.5 mm.'],
    ['magnet press fit', 'How much smaller the magnet hole is than the magnet. 0.35 mm, checked with the coupon.'],
    ['box', `${data.box ? `${data.box.length} × ${data.box.width} × ${data.box.height}` : '304.8 × 165.1 × 127'} mm outside.`],
  ];
  const dl = $('#params'); for (const [k, v] of rows) dl.append(h('dt', {}, k), h('dd', {}, v));
}

// ---------- boot ----------
async function boot() {
  initChrome(); renderRules(); initOptions(); initFiles(); initMaterials();
  const raw = await getJSON('data/parts.json'); const data = raw && normalizeData(raw);
  if (!data) { $('#hero-loading').textContent = 'The 3D model could not load.'; return; }
  initParams(data);
  artState.manifest = await getJSON('data/art-manifest.json');
  let hero = null;
  try { hero = initHero(data); } catch (e) { console.error(e); $('#hero-loading') && ($('#hero-loading').textContent = '3D needs WebGL, which this browser does not have.'); }
  if (artState.manifest) {
    for (const [fid, f] of Object.entries(artState.manifest.faces || {})) { const v = defaultVariant(f); if (v) artState.choice[fid] = v.id; }
    if (hero) applyArt(hero.model, 'burn').then(() => hero.viewer.kick());
  }
  let R = null; try { R = new StillRenderer(data); } catch (e) { console.error(e); }
  try { initEngraving(data); } catch (e) { console.error(e); }
  if (R) {
    await renderHow(data, R);
    await renderInventory(data, R);
    await renderSteps(data, R);
  }
}
boot();
