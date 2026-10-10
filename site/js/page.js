// Everything on the page that does not need three.js or WebGL: navigation, rules,
// the build guide text and pictures (pre-rendered), engraving comparisons (2D),
// downloads, materials, cutting options. The 3D module is loaded last and only
// upgrades the page; if it fails, nothing here is lost.
import { V } from './version.js';
import { RULES } from './rules.js';
import { buildSteps, stepParts, cleanName, HOW_CARDS, TOOLS, HARDWARE_FALLBACK, hwIcon, SVG_PAPER, LASER, withoutRemoved } from './guide.js';
import { inkCanvas, birchCanvas, artUrl } from './art2d.js';

export const $ = (s, el = document) => el.querySelector(s);
export const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v; else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null) e.append(k.nodeType ? k : document.createTextNode(String(k)));
  return e;
};
const vurl = u => u + (u.includes('?') ? '&' : '?') + 'v=' + V;
async function getText(url) { try { const r = await fetch(vurl(url)); return r.ok ? await r.text() : null; } catch { return null; } }
async function getJSON(url) { const t = await getText(url); try { return t ? JSON.parse(t) : null; } catch { return null; } }
const fmtUSD = n => '$' + Number(n).toFixed(2).replace(/\.00$/, '');
const hash = s => { let x = 5381; for (let i = 0; i < s.length; i++) x = ((x << 5) + x + s.charCodeAt(i)) | 0; return (x >>> 0).toString(16); };
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- chrome ----------
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
  // scroll cue on the strip of original photos
  const strip = $('.originals');
  if (strip) { const f = () => strip.parentElement.classList.toggle('more', strip.scrollLeft + strip.clientWidth < strip.scrollWidth - 8); strip.addEventListener('scroll', f, { passive: true }); addEventListener('resize', f); setTimeout(f, 300); }
}

function renderRules() {
  const ol = $('#rules');
  RULES.forEach((r, i) => ol.append(h('li', {},
    h('div', { class: 'rh' }, h('span', { class: 'num' }, i + 1), h('span', {}, r.title)),
    h('div', { html: r.svg }),
    h('p', {}, r.text))));
}

// pre-rendered pictures: img/render/index.json { hash, files: { key: path } }
function renderSrc(ctx, key) { const f = ctx.renders && ctx.renders.files && ctx.renders.files[key]; return f ? vurl(f) : null; }
function picSlot(ctx, key, alt, cls = 'pic') {
  const src = renderSrc(ctx, key);
  const img = h('img', { alt, loading: 'lazy', decoding: 'async', src: src || null, hidden: !src });
  const wrap = h('div', { class: cls }, img, src ? null : h('span', { class: 'ph' }, 'drawing…'));
  ctx.slots[key] = { img, wrap, set(url) { img.src = url; img.hidden = false; const ph = wrap.querySelector('.ph'); ph && ph.remove(); } };
  return wrap;
}

// ---------- how it works ----------
function renderHow(ctx) {
  const grid = $('#how-grid');
  for (const c of HOW_CARDS) {
    const fig = h('figure', {}, picSlot(ctx, 'how-' + c.id, c.alt, 'pic'));
    grid.append(h('article', { class: 'how' }, fig, h('div', { class: 'body' }, h('h3', {}, c.title), h('p', {}, c.text))));
  }
}

// ---------- inventory, hardware, tools ----------
function outlineSize(p) {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const [x, y] of p.outline || []) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  return p.size_mm || [x1 - x0, y1 - y0];
}
function renderInventory(ctx) {
  const data = ctx.data, inv = $('#inventory'); const seen = new Map();
  for (const p of data.parts) { const k = p.letter || p.id; if (!seen.has(k)) seen.set(k, { p, n: 0 }); seen.get(k).n++; }
  const items = [...seen.values()].sort((a, b) => String(a.p.letter).localeCompare(String(b.p.letter)));
  $('#fact-parts').textContent = data.parts.length + ' parts';
  for (const { p, n } of items) {
    const sz = outlineSize(p);
    const name = n > 1 ? cleanName(p.name) : p.name;
    inv.append(h('div', { class: 'inv' }, h('span', { class: 'letter' }, p.letter), h('span', { class: 'qty', 'aria-label': n + ' needed' }, '×' + n),
      picSlot(ctx, 'inv-' + p.letter, p.name, 'pic'), h('b', {}, name), h('small', {}, `${Math.round(sz[0])} × ${Math.round(sz[1])} mm`)));
  }
  const hw = $('#hardware');
  const hitems = (data.hardware && data.hardware.items && data.hardware.items.length) ? data.hardware.items : HARDWARE_FALLBACK;
  for (const it of hitems) hw.append(h('div', { class: 'hw', html: hwIcon(it.name) }, h('div', {}, h('b', {}, it.name), it.spares ? h('small', {}, `buy ${it.qty + it.spares} to have spares`) : null), h('span', { class: 'qty' }, '×' + it.qty)));
  for (const t of TOOLS) $('#tools').append(h('li', {}, t));
}

// ---------- steps (all text and anchors exist before any picture) ----------
function renderSteps(ctx) {
  const data = ctx.data;
  const steps = buildSteps(data); ctx.steps = steps;
  const list = $('#steps'), nav = $('#stepnav');
  const by = Object.fromEntries(data.parts.map(p => [p.id, p]));
  const artByPart = {};
  for (const [fid, f] of Object.entries((ctx.art && ctx.art.faces) || {})) artByPart[f.part_id || fid] = f;
  steps.forEach((s, i) => {
    const num = i + 1; s.num = num;
    let ids = stepParts(s);
    if (s.phase === 'drawer') ids = ids.filter(id => !/^t_/i.test(id));
    const letters = new Map(); for (const id of ids) { const p = by[id]; if (p && !letters.has(p.letter)) letters.set(p.letter, p); }
    let pic;
    if (s.focus === 'paper') pic = h('div', { class: 'step-pic', html: SVG_PAPER });
    else pic = h('div', { class: 'step-pic' }, picSlot(ctx, 'step-' + s.id, `Step ${num}: ${s.title || ''}`, 'pic'));
    if (s.focus === 'square') pic.append(h('span', { class: 'glue-flag' }, 'clamp'));
    const extra = null;
    const chips = h('div', { class: 'step-parts' },
      [...letters.values()].slice(0, 8).map(p => h('span', { class: 'pchip' }, h('span', { class: 'letter' }, p.letter), cleanName(p.name))),
      s.phase === 'drawer' ? h('span', { class: 'pchip tool' }, '× 2 drawers') : null,
      (s.hardware || []).map(x => h('span', { class: 'pchip hwc' }, x)),
      (s.tools || []).map(x => h('span', { class: 'pchip tool' }, x)));
    const li = h('li', { class: 'step', id: 'step-' + num },
      h('div', { class: 'step-head' }, h('span', { class: 'step-n' }, num), h('h3', {}, s.title || '')),
      pic, extra, chips, s.caption ? h('p', {}, s.caption) : null);
    list.append(li);
    nav.append(h('a', { href: '#step-' + num, 'aria-label': 'Step ' + num }, num));
  });
  // a deep link to a step now lands on the right card
  if (/^#step-\d+$/.test(location.hash)) { const el = document.getElementById(location.hash.slice(1)); el && el.scrollIntoView(); }
}

// ---------- engraving comparisons (2D; the 3D viewer subscribes) ----------
export const artState = { manifest: null, choice: {}, mode: 'burn', listeners: [], current: null };
const defaultVariant = f => (f.variants || []).find(v => v.default) || (f.variants || [])[0];
export function variantById(fid, vid) { const f = artState.manifest.faces[fid]; return (f.variants || []).find(v => v.id === vid) || defaultVariant(f); }
const FACE_NAMES = { left: 'Left wall', right: 'Right wall', front: 'Front', top: 'Top', lid: 'Lid', B_face: 'COLORS drawer', T_face: 'Lines drawer',
  B_left: 'COLORS, left side', B_right: 'COLORS, right side', T_left: 'Lines, left side', T_right: 'Lines, right side' };
const faceLabel = (fid, f) => FACE_NAMES[fid] || (f && f.title) || fid.replace(/_/g, ' ');
async function burnPreview(url, w) {
  const ink = await inkCanvas(url, [70, 40, 20], 0.86);
  const c = document.createElement('canvas'); const s = w / ink.width; c.width = w; c.height = Math.round(ink.height * s);
  const g = c.getContext('2d');
  g.drawImage(birchCanvas(1024, 512, 11), 0, 0, c.width, c.height);
  g.filter = 'blur(0.6px)'; g.drawImage(ink, 0, 0, c.width, c.height); g.filter = 'none';
  return c;
}
const cleanVariantLabel = l => String(l || '').replace(/\s*\([A-Z]\)\s*$/, '');
function linkedFaces(fid) {
  const man = artState.manifest; const groups = man.links || [['top', 'lid'], ['top_panel', 'sliding_lid']];
  const g = groups.find(x => x.includes(fid)); return g ? g.filter(x => x !== fid && man.faces[x]) : [];
}
function initEngraving(ctx) {
  const man = artState.manifest;
  const tabs = $('#facetabs'), vbox = $('#variants');
  if (!man || !Object.keys(man.faces || {}).length) { vbox.append(h('div', { class: 'soon' }, h('div', {}, h('b', {}, 'Art coming soon'), h('span', {}, 'The engraving files are still being drawn.')))); return; }
  for (const [fid, f] of Object.entries(man.faces)) { const v = defaultVariant(f); if (v) artState.choice[fid] = v.id; }
  const faces = Object.entries(man.faces);
  async function showFace(fid) {
    artState.current = fid;
    for (const b of tabs.children) b.setAttribute('aria-pressed', b.dataset.face === fid);
    const face = man.faces[fid]; vbox.innerHTML = '';
    const chosen = variantById(fid, artState.choice[fid]);
    for (const v of face.variants || []) {
      const png = artUrl({ png: v.png || v.svg });
      const inkImg = h('img', { src: vurl(v.svg ? artUrl({ svg: v.svg }) : png), alt: cleanVariantLabel(v.label) + ', line art', loading: 'lazy' });
      const burnSlot = h('div', { class: 'burnslot' });
      const on = v === chosen;
      const btn = h('button', { class: 'var' + (on ? ' on' : ''), 'aria-pressed': on, type: 'button' },
        h('div', { class: 'pair' }, inkImg, burnSlot),
        h('div', { class: 'lbls', 'aria-hidden': 'true' }, h('span', {}, 'line art'), h('span', {}, 'burned on birch')),
        h('div', { class: 'cap' }, h('div', {}, h('b', {}, cleanVariantLabel(v.label) || v.id), v.notes ? h('small', {}, ' ' + v.notes) : null), on ? h('span', { class: 'tag' }, 'on the box') : null));
      btn.addEventListener('click', () => {
        artState.choice[fid] = v.id;
        for (const other of linkedFaces(fid)) if ((man.faces[other].variants || []).some(x => x.id === v.id)) artState.choice[other] = v.id;
        showFace(fid);
        for (const f of artState.listeners) f('choice', fid);
      });
      vbox.append(btn);
      burnPreview(vurl(png), 700).then(c => { burnSlot.append(c); if (on) ctx.onBurn && ctx.onBurn(c); }).catch(e => console.warn(e.message));
    }
    const links = linkedFaces(fid);
    if (links.length) vbox.append(h('p', { class: 'small linknote' }, `The ${links.map(f => faceLabel(f, man.faces[f]).toLowerCase()).join(' and ')} changes with it: the art runs across both.`));
    for (const f of artState.listeners) f('face', fid);
  }
  artState.showFace = showFace;
  for (const [fid, face] of faces) {
    const nv = (face.variants || []).length;
    tabs.append(h('button', { type: 'button', 'data-face': fid, 'aria-pressed': 'false', onclick: () => showFace(fid) }, faceLabel(fid, face),
      nv > 1 ? h('span', { class: 'nv', 'aria-label': `, ${nv} versions` }, String(nv)) : null));
  }
  for (const b of document.querySelectorAll('.segbtn')) b.addEventListener('click', () => {
    artState.mode = b.dataset.mode;
    for (const x of document.querySelectorAll('.segbtn')) { x.classList.toggle('on', x === b); x.setAttribute('aria-pressed', x === b); }
    for (const f of artState.listeners) f('mode');
  });
  const io = new IntersectionObserver(es => { if (!es[0].isIntersecting) return; io.disconnect(); showFace(faces[0][0]); }, { rootMargin: '600px' });
  io.observe($('#engraving'));
}

// ---------- downloads ----------
const THICKS = Array.from({ length: 8 }, (_, i) => (2.8 + i * 0.1).toFixed(1));
function normThicknesses(m) {
  const out = {}; const src = m.thicknesses || m.by_thickness || {};
  const add = (t, f) => { if (f && !isNaN(+t)) out[Number(t).toFixed(1)] = f; };
  if (Array.isArray(src)) for (const e of src) add(e.thickness ?? e.mm ?? e.t, e);
  else for (const [t, f] of Object.entries(src)) add(t, f);
  return out;
}
const BED_NAMES = { ponoko: 'Ponoko', xtool_s1: 'xTool S1', xtool_p2: 'xTool P2', glowforge_pro: 'Glowforge Pro', generic_600x400: 'Any 600 × 400 mm bed', nycr: 'NYC Resistor (Epilog 32 × 20 in)', stock_12x24: '12 × 24 in sheets' };
function normBeds(m, t, entry) {
  const src = m.beds || m.layouts || {}; const out = [];
  const list = Array.isArray(src) ? src.map(b => [b.id || b.name, b]) : Object.entries(src);
  for (const [id, v] of list) {
    const o = typeof v === 'object' ? v : { sheets: v };
    const sheets = (entry && entry.sheets && entry.sheets[id]) ?? (o.sheets_by_thickness && o.sheets_by_thickness[t]) ?? o.sheets ?? o.sheet_count;
    out.push({ id, name: o.name || o.label || BED_NAMES[id] || id.replace(/_/g, ' '), size: o.width_mm ? `${Math.round(o.width_mm)} × ${Math.round(o.height_mm)} mm` : (o.size || ''), stock: o.stock || o.stock_note, note: o.note, sheets });
  }
  return out;
}
const fileUrl = (base, folder, f) => /^(https?:|\/)/.test(f) ? f : base + (folder && !f.includes('/') ? folder + '/' : '') + f;
const dlBtn = (href, label, cls = 'btn-line') => h('a', { class: 'btn ' + cls, href, download: '' }, label);
const soonBox = (title, text) => h('div', { class: 'soon', html: '<svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true"><rect x="6" y="4" width="28" height="36" rx="3" fill="#fff" stroke="#1d1b19" stroke-width="2.4"/><path d="M12 14h16M12 20h16M12 26h10" stroke="#1d1b19" stroke-width="2.2" stroke-linecap="round"/><circle cx="33" cy="33" r="8" fill="#f6d33c" stroke="#1d1b19" stroke-width="2.4"/><path d="M33 29v4l3 2" stroke="#1d1b19" stroke-width="2.2" stroke-linecap="round"/></svg>' }, h('div', {}, h('b', {}, title), h('span', {}, text)));
// kerf variants: entry.kerfs = { "0.12": { label, folder, zip, files } } (optional)
function kerfOptions(e) {
  const k = e && (e.kerfs || e.kerf_variants);
  if (!k) return null;
  const list = Array.isArray(k) ? k.map(x => [String(x.kerf ?? x.id), x]) : Object.entries(k);
  return list.map(([id, x]) => ({ id, label: x.label || x.name || `${id} mm kerf`, entry: x, default: !!x.default }));
}
function sheetList(base, folder, files, bedId) {
  const sheetFiles = files.filter(f => f.startsWith(bedId + '_sheet_'));
  const nums = [...new Set(sheetFiles.map(f => +f.match(/_sheet_(\d+)/)[1]))].sort((x, y) => x - y);
  return h('ul', { class: 'sheets' }, nums.map(k => h('li', {}, h('span', {}, 'Sheet ' + k),
    sheetFiles.filter(f => +f.match(/_sheet_(\d+)/)[1] === k).sort().reverse().map(f => h('a', { href: fileUrl(base, folder, f), download: '', 'aria-label': `Sheet ${k}, ${f.split('.').pop().toUpperCase()}` }, f.split('.').pop().toUpperCase())))));
}
async function initFiles() {
  const base = 'downloads/'; let man = await getJSON(base + 'manifest.json');
  const byT = man ? normThicknesses(man) : {};
  if (man && (man.status === 'pending' || !Object.keys(byT).length)) man = null;
  const thick = $('#thick'); let sel = (man && man.default_thickness) ? Number(man.default_thickness).toFixed(1) : '3.2'; let kerfSel = null;
  const guide = man && (man.coupon_guide || man.coupon_reading);
  renderCouponGuide(guide, base);
  function render() {
    for (const b of thick.children) { const on = b.dataset.t === sel; b.setAttribute('aria-checked', on); b.tabIndex = on ? 0 : -1; }
    $('#thick-read').textContent = `${sel} mm is about ${(sel / 25.4).toFixed(3)} in.`;
    const box = $('#box-dl'), coupon = $('#coupon-dl'), bedsEl = $('#beds'), kerfEl = $('#kerf');
    box.innerHTML = ''; coupon.innerHTML = ''; bedsEl.innerHTML = ''; kerfEl.innerHTML = '';
    if (!man) {
      box.append(soonBox('Files coming soon', 'The cut files for every thickness are being regenerated. This page will offer a zip, SVG and DXF for each one.'));
      coupon.append(soonBox('Coupon file coming soon', 'It ships with the box files.'));
      return;
    }
    let e = byT[sel];
    if (!e) { box.append(soonBox(`No files for ${sel} mm yet`, 'Pick another thickness, or generate your own from the source.')); return; }
    const kopts = kerfOptions(e);
    if (kopts && kopts.length) {
      if (!kerfSel || !kopts.some(k => k.id === kerfSel)) kerfSel = (kopts.find(k => k.default) || kopts[0]).id;
      kerfEl.append(h('p', { class: 'small' }, 'Laser kerf (the width the beam burns away):'),
        h('div', { class: 'seg seg-inline', role: 'group', 'aria-label': 'Kerf' }, kopts.map(k => h('button', { type: 'button', class: 'segbtn' + (k.id === kerfSel ? ' on' : ''), 'aria-pressed': k.id === kerfSel, onclick: () => { kerfSel = k.id; render(); } }, k.label))));
      e = { ...e, ...kopts.find(k => k.id === kerfSel).entry };
    }
    const files = Array.isArray(e.files) ? e.files : [], folder = e.folder || '';
    $('#legend-labels').hidden = !files.some(f => /label/i.test(f));
    const cps = files.filter(f => /coupon/i.test(f) && !/guide/i.test(f));
    if (cps.length) coupon.append(h('div', { class: 'dl-row' }, cps.map(f => dlBtn(fileUrl(base, folder, f), (/\.dxf$/i.test(f) ? 'Coupon DXF' : /\.pdf$/i.test(f) ? 'Coupon PDF' : 'Coupon SVG') + ` · ${sel} mm`))));
    else coupon.append(soonBox('Coupon file coming soon', 'It ships with the box files.'));
    box.append(h('p', {}, `Every part for ${sel} mm plywood, laid out on sheets for each laser bed below and color-coded for cutting. The zip holds all of them plus the coupon. Units are millimeters.`));
    const row = h('div', { class: 'dl-row' });
    if (e.zip) row.append(dlBtn(fileUrl(base, '', e.zip), `Download all (.zip, ${sel} mm)`, 'btn-ink'));
    const parts = e.parts_zip || e.parts_folder;
    if (parts) row.append(dlBtn(fileUrl(base, '', e.parts_zip || e.parts_folder), 'One file per part (zip)'));
    const extras = files.filter(f => /cut[-_]?only|labels?/i.test(f));
    for (const f of extras) row.append(dlBtn(fileUrl(base, folder, f), /label/i.test(f) ? 'Label layer' : 'Cut-only file'));
    box.append(row);
    const beds = normBeds(man, sel, e);
    if (beds.length) {
      bedsEl.append(h('h4', { class: 'bedh' }, 'Sheet layouts by laser bed'));
      const g = h('div', { class: 'beds' });
      for (const b of beds) g.append(h('div', { class: 'bed' }, h('b', {}, b.name),
        h('small', {}, [b.size, b.sheets != null ? `${b.sheets} sheet${b.sheets == 1 ? '' : 's'}` : null, b.stock].filter(Boolean).join(' · ')),
        b.note ? h('small', { class: 'bednote' }, b.note) : null, sheetList(base, folder, files, b.id)));
      bedsEl.append(g);
    }
  }
  THICKS.forEach(t => thick.append(h('button', { type: 'button', role: 'radio', 'data-t': t, onclick: () => { sel = t; render(); } }, t)));
  thick.addEventListener('keydown', ev => {
    const i = THICKS.indexOf(sel); let j = i;
    if (ev.key === 'ArrowRight' || ev.key === 'ArrowDown') j = Math.min(THICKS.length - 1, i + 1);
    else if (ev.key === 'ArrowLeft' || ev.key === 'ArrowUp') j = Math.max(0, i - 1);
    else return;
    ev.preventDefault(); sel = THICKS[j]; render(); thick.children[j].focus();
  });
  render();
}
// coupon reading guide from the downloads manifest:
// { diagram: "path.svg", intro, checks: [{ name, look, ok, fix }] }
function renderCouponGuide(g, base) {
  const el = $('#coupon-guide'); if (!el) return;
  if (!g) { el.append(h('p', { class: 'small' }, 'A diagram showing how to read each part of the coupon will appear here with the next set of files.')); return; }
  if (g.intro) el.append(h('p', {}, g.intro));
  if (g.diagram) el.append(h('img', { class: 'coupon-diagram', src: vurl(fileUrl(base, '', g.diagram)), alt: 'Coupon layout with each test labelled' }));
  const checks = g.checks || g.steps || [];
  if (checks.length) el.append(h('table', { class: 'tbl' }, h('thead', {}, h('tr', {}, h('th', {}, 'Test'), h('th', {}, 'What you see'), h('th', {}, 'What to do'))),
    h('tbody', {}, checks.map(c => h('tr', {}, h('td', {}, c.name || c.test || ''), h('td', {}, c.look || c.reading || ''), h('td', {}, c.fix || c.action || c.ok || ''))))));
}

// ---------- materials, cost summary, drawing kit ----------
async function initMaterials() {
  const d = await getJSON('data/materials.json'); const cat = await getJSON('data/drawing-catalog.json'); const kit = await getJSON('data/drawing-kit.json');
  const el = $('#materials-list');
  if (!d || !d.items) { el.append(soonBox('List coming soon', 'Exact product links are being checked.')); return; }
  if (d.checked) $('#mat-intro').textContent = `Everything besides the laser cutting. Links go to the listings we checked (${new Date(d.checked + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}); prices move, so treat them as a guide.`;
  const items = d.items.filter(i => !(i.category === 'Game supplies' && /\b(pens?|pencils?)\b/i.test(i.name)));
  const cats = [...new Set(items.map(i => i.category))];
  for (const c of cats) {
    const list = h('div', { class: 'mlist' });
    for (const i of items.filter(x => x.category === c)) {
      const pending = !i.url && i.price_usd == null;
      list.append(h('div', { class: 'mitem' + (pending ? ' pending' : '') + (i.optional || i.alternative ? ' opt' : '') },
        h('div', { class: 'top' }, h('b', {}, i.name), i.price_usd != null ? h('span', { class: 'price' }, fmtUSD(i.price_usd)) : null),
        i.spec ? h('span', { class: 'spec' }, i.spec) : null,
        i.note ? h('p', { class: 'note' }, i.note) : null,
        h('div', { class: 'foot2' }, h('span', { class: 'qty' }, pending ? 'Recommendations coming soon' : i.alternative ? 'Alternative' : i.optional ? 'Optional' : (i.qty ? `Use: ${i.qty}` : '')), i.url ? h('a', { class: 'buy', href: i.url, target: '_blank', rel: 'noopener' }, 'View listing') : null)));
    }
    el.append(h('div', { class: 'mcat' }, h('h3', {}, c), list));
  }
  // total: everything that isn't optional or an alternative
  const need = d.items.filter(i => i.price_usd != null && !i.optional && !i.alternative && !(i.category === 'Game supplies' && /\b(pens?|pencils?)\b/i.test(i.name)));
  const total = need.reduce((a, i) => a + i.price_usd, 0);
  $('#cost').append(h('div', { class: 'cost-card' },
    h('div', {}, h('b', {}, 'Supplies: about ' + fmtUSD(Math.round(total))), h('span', {}, 'for everything on this list except the optional and alternative items. Most packs cover a second box.')),
    h('div', {}, h('b', {}, 'Cutting: about $45–200'), h('span', {}, 'depending on where you get it cut (see below).'))));
  await renderCatalog(cat, kit);
}
const PRODUCT_ICON = '<svg viewBox="0 0 80 60" aria-hidden="true"><g fill="none" stroke="#1d1b19" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M10 44 L56 14 L66 22 L20 52 Z" fill="#f6d33c"/><path d="M56 14 L66 22 L72 12 Z" fill="#ecd6ae"/><path d="M20 52 L10 44 L8 54 Z" fill="#fff"/></g></svg>';
const CAT_FROM_ROLE = { color: ['colored-pencils', 'Colored pencils'], line: ['line-pens', 'Line pens'], graphite: ['graphite', 'Graphite pencils'], sharpener: ['sharpeners', 'Sharpeners'], eraser: ['erasers', 'Erasers'] };
function catalogFromKit(kit) {
  const cats = new Map(); const seen = new Set();
  for (const t of kit.tiers || []) for (const i of t.items || []) {
    if (seen.has(i.name)) continue; seen.add(i.name);
    const [id, name] = CAT_FROM_ROLE[i.role] || [i.role, i.role];
    if (!cats.has(id)) cats.set(id, { id, name, items: [] });
    cats.get(id).items.push({ name: i.name, price_usd: i.price_usd, url: i.url, good_for: i.why });
  }
  return { checked: kit.checked, categories: [...cats.values()] };
}
async function renderCatalog(cat, kit) {
  const el = $('#kit-tiers'); el.innerHTML = '';
  if (cat && !cat.categories) cat = null;
  if (!cat && kit && kit.tiers) cat = catalogFromKit(kit);
  if (!cat) { el.append(soonBox('Drawing kit: pens and pencils', 'Recommendations are coming soon.')); return; }
  const when = cat.checked ? new Date(cat.checked + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : null;
  $('#kit-intro').textContent = 'Mix and match. Every pencil and pen here fits the COLORS and Lines drawers lying flat; sets that come in tins go in loose. Ben, who designed the box, marked his favorites and the ones he uses.' + (when ? ` Prices checked ${when}.` : '');
  for (const c of cat.categories) {
    const grid = h('div', { class: 'cgrid' });
    for (const i of c.items || []) {
      const f = i.image_file || (i.asin ? i.asin + '.jpg' : null);
      grid.append(h('article', { class: 'prod' + (i.favorite ? ' fav' : '') },
        h('div', { class: 'pimg' }, f ? h('img', { src: vurl('img/products/' + f.split('/').pop()), alt: '', loading: 'lazy', width: 160, height: 160 }) : h('span', { class: 'noimg', html: PRODUCT_ICON }),
          i.favorite ? h('span', { class: 'badge fav' }, "Ben's favorite") : i.ben_uses ? h('span', { class: 'badge uses' }, 'Ben uses this') : null),
        h('div', { class: 'pbody' }, h('b', {}, i.name),
          h('span', { class: 'pack' }, [i.pack, i.price_usd != null ? fmtUSD(i.price_usd) : null].filter(Boolean).join(' · ')),
          i.good_for ? h('p', {}, i.good_for) : null,
          i.url ? h('a', { class: 'buy', href: i.url, target: '_blank', rel: 'noopener' }, 'View on Amazon') : null)));
    }
    el.append(h('section', { class: 'ccat' }, h('div', { class: 'ccat-head' }, h('h4', {}, c.name), c.blurb ? h('p', {}, c.blurb) : null), grid));
  }
}

// ---------- cutting options, laser table, maker params ----------
const ICON = {
  cloud: '<svg class="icon" viewBox="0 0 52 52" aria-hidden="true"><path d="M14 38h26a9 9 0 0 0 0-18 13 13 0 0 0-25-2 10 10 0 0 0-1 20z" fill="#fff" stroke="#1d1b19" stroke-width="2.6" stroke-linejoin="round"/><path d="M26 24v12m-6-6 6 6 6-6" stroke="#2f6fc9" stroke-width="2.6" fill="none" stroke-linecap="round"/></svg>',
  space: '<svg class="icon" viewBox="0 0 52 52" aria-hidden="true"><rect x="6" y="14" width="40" height="26" rx="4" fill="#f6d33c" stroke="#1d1b19" stroke-width="2.6"/><path d="M12 14V9h28v5M14 26h24" stroke="#1d1b19" stroke-width="2.6" fill="none"/><circle cx="38" cy="33" r="3" fill="#d8423a"/></svg>',
  shop: '<svg class="icon" viewBox="0 0 52 52" aria-hidden="true"><path d="M8 20h36v22H8z" fill="#fff" stroke="#1d1b19" stroke-width="2.6"/><path d="M6 20l5-10h30l5 10" fill="#3f9b4b" stroke="#1d1b19" stroke-width="2.6" stroke-linejoin="round"/><rect x="21" y="28" width="10" height="14" fill="#f6d33c" stroke="#1d1b19" stroke-width="2.4"/></svg>',
  laser: '<svg class="icon" viewBox="0 0 52 52" aria-hidden="true"><rect x="5" y="16" width="42" height="24" rx="3" fill="#fff" stroke="#1d1b19" stroke-width="2.6"/><path d="M5 24h42" stroke="#1d1b19" stroke-width="2.4"/><path d="M26 6v14" stroke="#d8423a" stroke-width="3" stroke-linecap="round"/><circle cx="26" cy="22" r="2.5" fill="#d8423a"/></svg>',
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
  const t = $('#laser');
  t.append(h('table', { class: 'tbl' },
    h('thead', {}, h('tr', {}, h('th', {}, 'Machine'), h('th', {}, 'Cut'), h('th', {}, 'Engrave'), h('th', {}, 'Source'))),
    h('tbody', {}, LASER.rows.map(r => h('tr', {}, h('td', {}, h('b', {}, r.machine)), h('td', {}, r.cut), h('td', {}, r.engrave), h('td', {}, h('a', { href: r.url, target: '_blank', rel: 'noopener' }, r.source)))))));
}
function initParams(data) {
  const T = data.box && data.box.thickness;
  const rows = [
    ['thickness', `Plywood thickness. Nominal 1/8 in (${T ? T.toFixed(3) : '3.175'} mm); the files come in 0.1 mm steps from 2.8 to 3.5 mm.`],
    ['kerf', 'The width of wood the laser burns away. The generator adds half of it back to every edge so joints come out snug.'],
    ['finger play', `Extra gap in each finger slot so joints close without forcing${data.box && data.box.finger_play ? ': ' + data.box.finger_play + ' mm' : ''}.`],
    ['slide clearance', 'Play around the drawers and the lid: 1.5 mm.'],
    ['magnet press fit', 'How much smaller the magnet hole is than the magnet: 0.35 mm.'],
    ['box', `${data.box ? `${data.box.length} × ${data.box.width} × ${data.box.height}` : '304.8 × 165.1 × 127'} mm outside.`],
  ];
  const dl = $('#params'); for (const [k, v] of rows) dl.append(h('dt', {}, k), h('dd', {}, v));
}

// ---------- boot ----------
async function boot() {
  initChrome(); renderRules(); initOptions(); initFiles(); initMaterials();
  const ctx = { slots: {}, artState, prerender: /[?&]prerender=1/.test(location.search), reduced: REDUCED };
  const [text, art, renders] = await Promise.all([getText('data/parts.json'), getJSON('data/art-manifest.json'), getJSON('img/render/index.json')]);
  ctx.renders = renders;
  if (!text) { $('#hero-loading').textContent = 'The parts list could not load.'; return; }
  ctx.data = withoutRemoved(JSON.parse(text)); ctx.dataHash = hash(text); ctx.art = art;
  artState.manifest = art;
  initParams(ctx.data);
  renderHow(ctx); renderInventory(ctx); renderSteps(ctx); initEngraving(ctx);
  // hero still for browsers without WebGL (replaced by the live model when it loads)
  const heroSrc = renderSrc(ctx, 'hero');
  const noGL = () => {
    $('#hero-stage').classList.add('nogl');
    const l = $('#hero-loading'); if (l) l.remove();
    if (heroSrc) $('#hero-stage').prepend(h('img', { class: 'hero-still', src: heroSrc, alt: 'The Fax Machine box in birch plywood, with its engraved art' }));
    $('#art-stage-note').hidden = false;
    ctx.onBurn = c => { const s = $('#art-still'); s.innerHTML = ''; const k = c.cloneNode(); k.getContext('2d').drawImage(c, 0, 0); s.append(k); };
    // show the current face's burn preview in the stage
    const sync = () => { const cur = $('#variants .var.on canvas'); if (cur && cur !== ctx._still) { ctx._still = cur; ctx.onBurn(cur); } };
    new MutationObserver(sync).observe($('#variants'), { childList: true, subtree: true }); sync();
  };
  const hasGL = (() => { try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; } })();
  if (!hasGL) { noGL(); return; }
  try { const m = await import('./render3d.js'); await m.start(ctx); }
  catch (e) { console.warn('3D unavailable:', e && e.message); noGL(); }
}
boot();
