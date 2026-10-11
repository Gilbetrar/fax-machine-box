// Everything on the page that does not need three.js or WebGL: navigation, rules,
// the build guide text and pictures (pre-rendered), engraving comparisons (2D),
// downloads, materials, cutting options. The 3D module is loaded last and only
// upgrades the page; if it fails, nothing here is lost.
import { V } from './version.js';
import { RULES } from './rules.js';
import { buildSteps, stepParts, cleanName, HOW_CARDS, TOOLS, HARDWARE_FALLBACK, hwIcon, SVG_PAPER, LASER } from './guide.js';
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
  const hint = document.getElementById('stage-hint'); if (hint && matchMedia('(pointer: coarse)').matches) hint.textContent = 'Drag to turn · tap a drawer or the lid';
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
      const thumb = v.png_th ? artUrl({ png: v.png_th }) : png;   // small picture for the card; full SVG on request
      const inkImg = h('img', { src: vurl(thumb), alt: cleanVariantLabel(v.label) + ', line art', loading: 'lazy', decoding: 'async' });
      const burnSlot = h('div', { class: 'burnslot' });
      const on = v === chosen;
      const btn = h('button', { class: 'var' + (on ? ' on' : ''), 'aria-pressed': on, type: 'button' },
        h('div', { class: 'pair' }, inkImg, burnSlot),
        h('div', { class: 'lbls', 'aria-hidden': 'true' }, h('span', {}, 'line art'), h('span', {}, 'burned on birch')),
        h('div', { class: 'cap' }, h('div', {}, h('b', {}, cleanVariantLabel(v.label) || v.id), v.notes ? h('small', {}, ' ' + v.notes) : null,
          v.svg ? h('a', { class: 'fullsize', href: vurl(artUrl({ svg: v.svg })), target: '_blank', rel: 'noopener', onclick: e => e.stopPropagation() }, 'Full-size line art') : null), on ? h('span', { class: 'tag' }, 'on the box') : null));
      btn.addEventListener('click', () => {
        artState.choice[fid] = v.id;
        for (const other of linkedFaces(fid)) if ((man.faces[other].variants || []).some(x => x.id === v.id)) artState.choice[other] = v.id;
        showFace(fid);
        for (const f of artState.listeners) f('choice', fid);
      });
      vbox.append(btn);
      burnPreview(vurl(thumb), 560).then(c => { burnSlot.append(c); if (on) ctx.onBurn && ctx.onBurn(c); }).catch(e => console.warn(e.message));
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
// downloads/manifest.json, schema 3 (see site/downloads/README.md). Every field is optional:
// missing pieces show a short "coming soon" note instead of breaking the section.
const DL = 'downloads/';
export const dlState = { man: undefined, ready: null };
const THICKS = Array.from({ length: 8 }, (_, i) => (2.8 + i * 0.1).toFixed(1));
const fileUrl = f => /^(https?:|\/)/.test(f) ? f : DL + f + '?v=' + V;
const mm2 = x => Number(x).toFixed(2);
const mm1 = x => Number(x).toFixed(1);
const dlBtn = (href, label, cls = 'btn-line') => h('a', { class: 'btn ' + cls, href: fileUrl(href), download: '' }, label);
const soonBox = (title, text) => h('div', { class: 'soon', html: '<svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true"><rect x="6" y="4" width="28" height="36" rx="3" fill="#fff" stroke="#1d1b19" stroke-width="2.4"/><path d="M12 14h16M12 20h16M12 26h10" stroke="#1d1b19" stroke-width="2.2" stroke-linecap="round"/><circle cx="33" cy="33" r="8" fill="#f6d33c" stroke="#1d1b19" stroke-width="2.4"/><path d="M33 29v4l3 2" stroke="#1d1b19" stroke-width="2.2" stroke-linecap="round"/></svg>' }, h('div', {}, h('b', {}, title), h('span', {}, text)));
const tidy = s => String(s || '').replace(/(\d)\s*x\s*(\d)/g, '$1 × $2').replace(/\b0\.2 mm/g, '0.20 mm').replace(/\bi engraved ticks (above|below|between) slot i( and the magnet holes)?/g, (m, w, x) => `one engraved tick ${w === 'between' ? 'beside' : w} the first slot, two beside the second, and so on${x ? ', between the slots and the magnet holes' : ''}`).replace(/rounded to 0\.05\b/g, 'rounded to the nearest 0.05 mm').replace(/\(see finger_joints\)/g, '(see Finger joints below)').replace(/the narrowest slot your plywood slides into without force/g, 'the narrowest slot your plywood slides into freely, with a visible gap');
const sheetsTxt = n => n == null ? '' : `${n} sheet${n == 1 ? '' : 's'}`;
function seg(label, opts, cur, onPick) {
  return h('div', { class: 'seg seg-inline', role: 'group', 'aria-label': label },
    opts.map(o => h('button', { type: 'button', class: 'segbtn' + (o.id === cur ? ' on' : ''), 'aria-pressed': o.id === cur, onclick: () => onPick(o.id) }, o.label)));
}
async function initFiles() {
  let man = await getJSON(DL + 'manifest.json');
  if (man && (!man.thicknesses || !Object.keys(man.thicknesses).length)) man = null;
  dlState.man = man; dlState.ready && dlState.ready(man);
  const st = { t: man && man.default_thickness ? Number(man.default_thickness).toFixed(1) : '3.2', kerf: 'co2', ver: 'cut_engrave' };
  const kerfs = man && man.kerfs ? Object.entries(man.kerfs).map(([id, k]) => ({ id, mm: k.kerf_mm, label: tidy(k.label) })) : [];
  const versions = man && man.versions ? Object.entries(man.versions).map(([id, v]) => ({ id, label: v.label, text: v.text })) : [];
  if (versions.length && !versions.some(v => v.id === st.ver)) st.ver = versions[0].id;
  if (kerfs.length && !kerfs.some(k => k.id === st.kerf)) st.kerf = kerfs[0].id;
  const thick = $('#thick');
  function render() {
    for (const b of thick.children) { const on = b.dataset.t === st.t; b.setAttribute('aria-checked', on); b.tabIndex = on ? 0 : -1; }
    $('#thick-read').textContent = `${st.t} mm is about ${(st.t / 25.4).toFixed(3)} in.`;
    const box = $('#box-dl'), coupon = $('#coupon-dl'), bedsEl = $('#beds'), kerfEl = $('#kerf'), wall = $('#wall-id');
    for (const el of [box, coupon, bedsEl, kerfEl, wall]) el.innerHTML = '';
    if (!man) {
      box.append(soonBox('Files coming soon', 'The cut files for every thickness are being regenerated.'));
      coupon.append(soonBox('Coupon file coming soon', 'It ships with the box files.'));
      return;
    }
    const T = man.thicknesses[st.t];
    if (!T) { box.append(soonBox(`No files for ${st.t} mm yet`, 'Pick another thickness.')); return; }
    if (T.wall_id) wall.append(h('b', {}, 'Telling the side walls apart: '), `${T.wall_id.rule || 'the left wall has one more divider hole.'} At ${st.t} mm the left wall has ${T.wall_id.left_divider_holes} and the right wall ${T.wall_id.right_divider_holes}.`);
    // coupon (per kerf in schema 4)
    const Kc = (T.kerfs && Object.values(T.kerfs).find(k => k.id === st.kerf)) || null;
    const c = (Kc && Kc.coupon) || T.coupon;
    if (c) coupon.append(h('div', { class: 'dl-row' },
      c.svg_marked ? dlBtn(c.svg_marked, 'Coupon with tick marks, SVG', 'btn-ink') : null, c.dxf_marked ? dlBtn(c.dxf_marked, 'DXF') : null,
      c.svg ? dlBtn(c.svg, 'Cut-only coupon, SVG') : null, c.dxf ? dlBtn(c.dxf, 'DXF') : null),
      h('p', { class: 'small' }, `For ${st.t} mm plywood${Kc && Kc.coupon ? ` and the ${mm2(Kc.kerf_mm)} mm kerf` : ''}. The marked version engraves small ticks that make the tests easier to read; use the cut-only one if your service only cuts.`));
    else coupon.append(soonBox('Coupon file coming soon', 'It ships with the box files.'));
    // kerf and version pickers
    const K = (T.kerfs && Object.values(T.kerfs).find(k => k.id === st.kerf)) || null;
    if (kerfs.length) kerfEl.append(h('p', { class: 'pick-label' }, 'Laser kerf: the width the beam burns away. Your coupon\'s kerf square tells you which.'), seg('Kerf', kerfs, st.kerf, id => { st.kerf = id; render(); }));
    if (versions.length) kerfEl.append(h('p', { class: 'pick-label' }, 'What the files contain:'), seg('File version', versions, st.ver, id => { st.ver = id; render(); }),
      h('p', { class: 'small vtext' }, tidy((versions.find(v => v.id === st.ver) || {}).text)));
    if (!K) { box.append(soonBox('No files for this kerf yet', 'Pick another kerf.')); return; }
    const V = K[st.ver];
    const row = h('div', { class: 'dl-row' });
    if (V && V.zip) row.append(dlBtn(V.zip, `Download all beds (.zip, ${st.t} mm, ${mm2(K.kerf_mm)} mm kerf)`, 'btn-ink'));
    else if (V && V.beds) {   // cut + engrave comes as one zip per bed
      const list = Object.entries(V.beds);
      if (list.length) box.append(h('p', { class: 'pick-label' }, 'Cut + engrave files are laid out for one bed at a time, so there is one zip per bed (no all-beds zip):'));
      for (const [bid, e] of list) row.append(dlBtn(e.zip, `${tidy(((man.beds || {})[bid] || {}).label || bid).split(' (')[0]} (.zip)`, 'btn-ink'));
    }
    if (T.parts && T.parts.zip) row.append(dlBtn(T.parts.zip, 'One file per part (.zip)'));
    box.append(row);
    if (T.parts && T.parts.zip) box.append(h('p', { class: 'small' }, 'The one-file-per-part set has no kerf added, for services such as SendCutSend that apply their own; it also has the engraving for each art part on its own.'));
    // beds
    renderCouponGuide(man, st);
    const beds = Object.entries(man.beds || {});
    if (!beds.length) return;
    const tbl = h('table', { class: 'tbl beds-tbl' },
      h('thead', {}, h('tr', {}, h('th', {}, 'Laser bed'), h('th', {}, 'Stock you need'), h('th', {}, 'Sheets'), h('th', {}, ''))));
    const tb = h('tbody', {});
    for (const [id, b] of beds) {
      let sheets = null, href = null, why = '';
      const kerfOK = !b.kerfs || b.kerfs.includes(st.kerf);
      if (!kerfOK) { const kk = man.kerfs && man.kerfs[b.kerfs[0]]; why = `Cuts with a ${kk ? mm2(kk.kerf_mm) : ''} mm kerf: pick the ${kk ? mm2(kk.kerf_mm) + ' mm' : b.kerfs[0]} kerf above to get its files.`; }
      else if (st.ver === 'cut_engrave') {
        const e = V && V.beds && V.beds[id];
        if (e) { sheets = e.sheets; href = e.zip; } else why = 'Engraved files for this bed come with the CO2 kerf.';
        if (!e && b.engrave_kerfs && b.engrave_kerfs.length) why = `Engraved files for this bed use the ${b.engrave_kerfs.map(k => (kerfs.find(x => x.id === k) || { label: k }).label.split(' (')[0]).join(' or ')} kerf.`;
      } else { sheets = V && V.sheets ? V.sheets[id] : null; if (V && V.zip && sheets != null) href = V.zip; if (sheets == null) why = 'Not in this set.'; }
      tb.append(h('tr', {},
        h('td', { 'data-l': 'Laser bed' }, h('b', {}, tidy(b.label)), b.note ? h('small', { class: 'bednote' }, tidy(b.note)) : null),
        h('td', { 'data-l': 'Stock' }, tidy(b.stock && b.stock.name)),
        h('td', { class: 'num', 'data-l': 'Sheets' }, sheets != null ? String(sheets) : '–'),
        h('td', {}, href ? h('a', { class: 'sheetdl', href: fileUrl(href), download: '' }, st.ver === 'cut_engrave' ? 'Download' : 'In the zip') : h('small', {}, why))));
    }
    tbl.append(tb);
    bedsEl.append(h('h4', { class: 'bedh' }, `Sheet layouts for ${st.t} mm, ${mm2(K.kerf_mm)} mm kerf`), h('div', { class: 'tbl-wrap' }, tbl));
  }
  THICKS.forEach(t => thick.append(h('button', { type: 'button', role: 'radio', 'data-t': t, onclick: () => { st.t = t; render(); } }, t)));
  thick.addEventListener('keydown', ev => {
    const i = THICKS.indexOf(st.t); let j = i;
    if (ev.key === 'ArrowRight' || ev.key === 'ArrowDown') j = Math.min(THICKS.length - 1, i + 1);
    else if (ev.key === 'ArrowLeft' || ev.key === 'ArrowUp') j = Math.max(0, i - 1);
    else return;
    ev.preventDefault(); st.t = THICKS[j]; render(); thick.children[j].focus();
  });
  render();
  if (man) { renderCouponGuide(man, st); renderLegend(man); }
  else renderCouponGuide(null, st);
}
function renderLegend(man) {
  const e = man.engrave; if (!e || !e.colors) return;
  const L = $('#legend'); L.innerHTML = '';
  const name = c => ({ '#0000ff': 'Blue', '#808080': 'Gray', '#ff0000': 'Red', '#000000': 'Black' })[String(c).toLowerCase()] || c;
  const rows = [['cut', 'is cut.', 'Hairline vector lines that go through the sheet (layer CUT in the DXF).'],
    ['engrave_fill', 'fill is area engrave.', 'The art: filled shapes to raster engrave (layer ENGRAVE). Never cut through.'],
    ['marks', 'hairline is a line engrave.', 'Single-line marks: part letters, joint numbers, faceplate glue-up lines and coupon ticks (layer LABELS). They are optional.'],
    ['engrave_line', 'is a scored line.', 'Faceplate glue-up guides.'],
    ['labels', 'is labels.', 'Part letters and joint numbers on the inside faces.']];
  for (const [k, a, b] of rows) if (e.colors[k]) L.append(h('li', {}, h('span', { class: 'sw' + (k === 'engrave_fill' ? ' fill' : ''), style: `--c:${e.colors[k]}` }), h('span', {}, h('b', {}, `${name(e.colors[k])} ${a}`), ' ' + b)));
  $('#dxf-note').textContent = [e.colour_note, e.dxf_note].filter(Boolean).map(t => tidy(t.replace(/\s*\(https?:[^)]*\)/, ''))).join(' ');
}
// the coupon: layout drawn from the manifest, plus how to read each test
const FEATURE_NAMES = { kerf_square: 'Kerf square', thickness_slots: 'Thickness slots', magnet_holes: 'Magnet holes', finger_joints: 'Finger joints', lid_slot: 'Lid slot' };
function couponSVG(layout) {
  const W = Math.max(...layout.map(r => r.x_mm + r.width_mm)) + 5, H = Math.max(...layout.map(r => r.y_mm + r.height_mm)) + 5;
  const col = { Q: '#fdf5cf', R: '#e7f0fb', S: '#e6f3e6', K: '#fbe3df' };
  let o = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Coupon layout"><rect x="0.5" y="0.5" width="${W - 1}" height="${H - 1}" fill="#fff" stroke="#c9bfae" stroke-width="0.6" stroke-dasharray="3 2"/>`;
  for (const r of layout) {
    const L = r.part[0]; const y = r.y_mm;
    o += `<rect x="${r.x_mm}" y="${y}" width="${r.width_mm}" height="${r.height_mm}" rx="1" fill="${col[L] || '#eee'}" stroke="#1d1b19" stroke-width="0.7"/>`;
    o += `<text x="${r.x_mm + r.width_mm / 2}" y="${y + r.height_mm / 2 + 2.6}" font-family="Rubik, sans-serif" font-weight="800" font-size="7.5" text-anchor="middle" fill="#1d1b19">${L}</text>`;
  }
  return o + '</svg>';
}
const couponCache = new Map();
async function realCoupon(file, layout) {
  // the actual coupon drawing (marked version), with each piece shaded and lettered from the layout
  if (!couponCache.has(file)) couponCache.set(file, getText(DL + file));
  const txt = await couponCache.get(file); if (!txt) return null;
  const d = new DOMParser().parseFromString(txt, 'image/svg+xml'); const svg = d.documentElement;
  if (!svg || svg.nodeName !== 'svg') return null;
  svg.removeAttribute('width'); svg.removeAttribute('height'); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', 'The test-fit coupon');
  const NS = 'http://www.w3.org/2000/svg';
  const col = { Q: '#fdf5cf', R: '#e7f0fb', S: '#e6f3e6', K: '#fbe3df' };
  const under = d.createElementNS(NS, 'g'), over = d.createElementNS(NS, 'g');
  for (const r of layout || []) {
    const L = r.part[0];
    const rect = d.createElementNS(NS, 'rect'); for (const [k, v] of Object.entries({ x: r.x_mm, y: r.y_mm, width: r.width_mm, height: r.height_mm, fill: col[L] || '#eee' })) rect.setAttribute(k, v); under.append(rect);
    const t = d.createElementNS(NS, 'text'); for (const [k, v] of Object.entries({ x: r.x_mm + r.width_mm - 3, y: r.y_mm + 7, 'font-family': 'Rubik, sans-serif', 'font-weight': 800, 'font-size': 6, 'text-anchor': 'end', fill: '#1d1b19' })) t.setAttribute(k, v); t.textContent = L; over.append(t);
  }
  svg.insertBefore(under, svg.firstChild); svg.append(over);
  return new XMLSerializer().serializeToString(svg);
}
function renderCouponGuide(man, st) {
  const el = $('#coupon-guide'); el.innerHTML = '';
  if (!man) { el.append(h('p', { class: 'small' }, 'The reading guide comes with the next set of files.')); return; }
  const g = man.coupon_guide; const T = man.thicknesses[st.t] || Object.values(man.thicknesses)[0];
  if (!g) { el.append(h('p', { class: 'small' }, 'The reading guide comes with the next set of files.')); return; }
  const Kc = T && T.kerfs && Object.values(T.kerfs).find(k => k.id === st.kerf);
  const cp = (Kc && Kc.coupon) || (T && T.coupon) || {};
  const layout = cp.layout;
  const left = h('div', { class: 'cg-left' });
  if (layout && layout.length) {
    const box = h('div', { class: 'cg-svg', html: couponSVG(layout) });
    left.append(box);
    const f = cp.svg_marked || cp.svg;
    if (f) realCoupon(f, layout).then(s => { if (s) box.innerHTML = s; });
    if (g.orientation) left.append(h('p', { class: 'small' }, tidy(g.orientation)));
    const pieces = {}; for (const r of layout) { const L = r.part[0]; (pieces[L] = pieces[L] || []).push(r.part.replace(/^\w\s+Coupon:\s*/, '')); }
    left.append(h('ul', { class: 'cg-keys' }, Object.entries(pieces).map(([L, ps]) => h('li', {}, h('span', { class: 'letter' }, L), h('span', {}, tidy([...new Set(ps.map(p => p.replace(/, (finger|hole) piece$/, '').replace(/, kerf [\d.]+/, '')))].join('; ')))))));
  }
  if (g.order && g.order.length) left.append(h('ol', { class: 'cg-order' }, g.order.map(s => h('li', {}, tidy(s)))));
  const right = h('div', { class: 'cg-right' });
  for (const f of g.features || []) {
    const lines = [];
    if (f.measure) lines.push(['Measure', f.measure]);
    if (f.reading) lines.push(['Look for', f.reading]);
    if (f.identify) lines.push(['Which is which', f.identify]);
    if (f.ticks) lines.push(['Tick marks', f.ticks]);
    if (f.formula) lines.push(['Work it out', f.formula]);
    if (f.rounding) lines.push(['Rounding', f.rounding]);
    if (f.id === 'thickness_slots') lines.push(['Range', 'The box files cover 2.8 to 3.5 mm. Plywood outside that range is not supported.']);
    if (f.choose) lines.push(['Pick', f.choose.map(c => `${mm2(c.kerf_mm)} mm: ${(man.kerfs && man.kerfs[c.set] ? man.kerfs[c.set].label.split(' (')[0] : c.set)} files`).join(' · ')]);
    if (f.drawn_widths_mm) lines.push(['Drawn widths', `${mm1(f.drawn_widths_mm[0])} to ${mm1(f.drawn_widths_mm[f.drawn_widths_mm.length - 1])} mm in ${mm1(f.drawn_widths_mm[1] - f.drawn_widths_mm[0])} mm steps`]);
    if (f.drawn_diameters_mm) lines.push(['Drawn holes', f.drawn_diameters_mm.map(mm1).join(', ') + ' mm']);
    if (f.right) lines.push(['Right', f.right]);
    for (const k of ['tight_along_the_finger', 'loose_along_the_finger', 'tight_through_the_slot', 'loose_through_the_slot']) if (typeof f[k] === 'string') lines.push([k.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase()), f[k]]);
    for (const [k, label] of [['along_the_fingers', 'Along the fingers'], ['through_the_thickness', 'Through the thickness']]) {
      const g = f[k]; if (!g || typeof g !== 'object') continue;
      if (g.what) lines.push([label, g.what]);
      if (g.tight) lines.push(['  Too tight', g.tight]);
      if (g.loose) lines.push(['  Too loose', g.loose]);
    }
    if (f.then) lines.push(['Then', f.then]);
    right.append(h('div', { class: 'cg-feat' }, h('h4', {}, h('span', { class: 'letter' }, f.part || '?'), FEATURE_NAMES[f.id] || f.id.replace(/_/g, ' ')),
      h('dl', {}, lines.flatMap(([k, v]) => [h('dt', {}, k), h('dd', {}, tidy(v))]))));
  }
  el.append(h('div', { class: 'cg' }, left, right));
}

// joint map: the matching numbers on the inside faces, drawn on each part's outline
function renderJoints(ctx) {
  const el = $('#joints'); if (!el) return;
  const go = man => {
    el.innerHTML = '';
    const T = man && (man.thicknesses[(man.default_thickness && Number(man.default_thickness).toFixed(1)) || '3.2'] || Object.values(man.thicknesses)[0]);
    const jm = T && T.joint_map; if (!jm) { el.closest('.joints-wrap').hidden = true; return; }
    const byLetter = {}; for (const p of ctx.data.parts) if (!byLetter[p.letter]) byLetter[p.letter] = p;
    const marks = {}; for (const j of jm.joints) for (const q of j.parts) (marks[q.part] = marks[q.part] || []).push({ id: j.id, x: q.x_mm, y: q.y_mm });
    const lab = jm.labelled_on_inside_face || {}; const unl = new Set(jm.art_parts_unlabelled || []);
    const grid = h('div', { class: 'jgrid' });
    for (const L of Object.keys(lab).sort()) {
      const p = byLetter[L]; if (!p || unl.has(L) || !(lab[L] || []).length) continue;
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; for (const [x, y] of p.outline) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
      const pad = 8, w = x1 - x0 + 2 * pad, hh = y1 - y0 + 2 * pad, fs = Math.max(9, Math.min(w, hh) / 9);
      const pts = p.outline.map(([x, y]) => `${(x - x0 + pad).toFixed(1)},${(y1 - y + pad).toFixed(1)}`).join(' ');
      const tags = (marks[L] || []).filter(m => lab[L].includes(m.id)).map(m => {
        const cx = Math.min(Math.max(m.x - x0 + pad, fs), w - fs), cy = Math.min(Math.max(y1 - m.y + pad, fs), hh - fs);
        return `<g><circle cx="${cx}" cy="${cy}" r="${fs * 0.95}" fill="#fff" stroke="#1d1b19" stroke-width="${fs / 7}"/><text x="${cx}" y="${cy + fs * 0.36}" font-family="Rubik, sans-serif" font-weight="800" font-size="${fs}" text-anchor="middle" fill="#1d1b19">${m.id}</text></g>`;
      }).join('');
      grid.append(h('figure', { class: 'jpart' }, h('div', { html: `<svg viewBox="0 0 ${w.toFixed(1)} ${hh.toFixed(1)}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${p.name} with its joint numbers"><polygon points="${pts}" fill="#f2d9a8" stroke="#1d1b19" stroke-width="${Math.max(0.8, fs / 10)}" stroke-linejoin="round"/>${tags}</svg>` }),
        h('figcaption', {}, h('span', { class: 'letter' }, L), cleanName(p.name))));
    }
    el.append(grid);
    const unlNames = [...unl].map(L => byLetter[L] && cleanName(byLetter[L].name)).filter(Boolean);
    if (unlNames.length) el.append(h('p', { class: 'small' }, `The parts with art (${[...new Set(unlNames)].join(', ').toLowerCase()}) have no numbers in the engraved files, so their outside stays clean, and a joint between an art part and a plain part shows its number on the plain part only. The cut + labels files number them too. The art shows which way they face.`));
  };
  if (dlState.man !== undefined) go(dlState.man); else dlState.ready = go;
}

// ---------- materials, cost summary, drawing kit ----------
async function initMaterials() {
  const d = await getJSON('data/materials.json'); const cat = await getJSON('data/drawing-catalog.json'); const kit = await getJSON('data/drawing-kit.json');
  const el = $('#materials-list');
  if (!d || !d.items) { el.append(soonBox('List coming soon', 'Exact product links are being checked.')); return; }
  if (d.checked) $('#mat-intro').textContent = `Everything besides the laser cutting. Links go to the listings we checked (${new Date(d.checked + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}); prices move, so treat them as a guide.`;
  const man = await new Promise(r => { if (dlState.man !== undefined) r(dlState.man); else { const prev = dlState.ready; dlState.ready = m => { prev && prev(m); r(m); }; } });
  const stock = man && man.beds && Object.entries(man.beds).find(([, b]) => /12 x 24/.test((b.stock && b.stock.name) || '') && b.stock.width_mm > 600);
  const t32 = man && man.thicknesses && man.thicknesses['3.2'];
  const n1224 = (man && man.stock_12x24_sheets_per_box) || stock && t32 && t32.kerfs && Object.values(t32.kerfs).map(k => k.cut_only && k.cut_only.sheets && k.cut_only.sheets[stock[0]]).find(n => n != null);
  // every plywood number comes from the 12 x 24 in layout's sheet count and the listed pack price
  const ply = d.items.find(i => /12 × 24 in, box of (\d+)/.test(i.name));
  if (ply && n1224) {
    const pack = +ply.name.match(/box of (\d+)/)[1]; const boxes = Math.floor(pack / n1224); const per = ply.price_usd / pack * n1224;
    ply.qty = n1224;
    const s1 = t32 && t32.kerfs && Object.values(t32.kerfs).map(k => k.cut_only && k.cut_only.sheets && k.cut_only.sheets.xtool_s1).find(n => n != null);
    ply.note = `The 12 × 24 in layout (xTool P2 bed, or any bed that takes a whole 12 × 24 in sheet) uses ${n1224} sheets per box, so a box of ${pack} covers ${boxes} boxes, about ${fmtUSD(Math.round(per))} of plywood per box.` + (s1 ? ` The xTool S1 layout cuts each sheet to 498 mm and needs ${s1}.` : '') + ' Other beds are listed with their sheet counts under Cut files. Measure the thickness before you pick a cut file.';
    const t = $('#ply-cost'); if (t) t.textContent = `about ${fmtUSD(Math.round(per))}: ${n1224} sheets of 12 × 24 in with the 12 × 24 in layout`;
  }
  for (const i of d.items) if (i.note) i.note = i.note.replace('{SHEETS_12x24}', n1224 || 'four');
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
  $('#kit-intro').textContent = 'Choose any mix from the lists below. Every pencil and pen here fits the COLORS and Lines drawers lying flat; sets that come in tins go in loose. Ben, who designed the box, marked his favorites and the ones he uses.' + (when ? ` Prices checked ${when}.` : '');
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
      pts: ['NYC Resistor (Boerum Hill): $1 per minute self-serve after an $85 class; Epilog 60 W, 32 × 20 in bed', 'Engraves and cuts in one or two craft nights', 'Bring your own plywood'] },
    { icon: 'cloud', title: 'Online cutting service', cost: '~$150–200', sub: 'cut only, plus shipping',
      pts: ['SendCutSend: instant guest quote about $195 for 1/8 in Baltic birch; DXF files; no wood engraving', 'Ponoko: about $153 cut-only; engraving priced by machine time (adds roughly $60–200)', 'Easiest if you skip the art'] },
    { icon: 'shop', title: 'A local laser shop', cost: '$200+', sub: 'minimum order',
      pts: ['Fabberz (Industry City): $200 minimum, per-minute pricing', 'DIVISION and PrintAWorld quote by file', 'Good if you want someone else to run the machine'] },
    { icon: 'laser', title: 'Your own laser', cost: '$1,700+', sub: 'one-time, for many boxes',
      pts: ['xTool S1 diode (498 × 319 mm bed) from $1,699; about 2 to 5 hours per box', 'xTool P2S 55 W CO2 from $2,999; under 2 hours', 'Needs real ventilation: birch plywood smoke is harsh'] },
  ];
  const el = $('#options');
  for (const o of opts) el.append(h('article', { class: 'opt' + (o.rec ? ' rec' : ''), html: ICON[o.icon] }, o.rec ? h('span', { class: 'badge' }, 'recommended') : null, h('h3', {}, o.title), h('div', { class: 'cost' }, o.cost, h('small', {}, o.sub)), h('ul', {}, o.pts.map(p => h('li', {}, p, p === 'Bring your own plywood' ? [' (', h('span', { id: 'ply-cost' }, 'see the materials list'), ')'] : null)))));
  const t = $('#laser');
  t.append(h('table', { class: 'tbl laser-tbl' },
    h('thead', {}, h('tr', {}, h('th', {}, 'Machine'), h('th', {}, 'Cut'), h('th', {}, 'Engrave'), h('th', {}, 'Source'))),
    h('tbody', {}, LASER.rows.map(r => h('tr', {}, h('td', {}, h('b', {}, r.machine)), h('td', { 'data-l': 'Cut' }, r.cut), h('td', { 'data-l': 'Engrave' }, r.engrave), h('td', { 'data-l': 'Source' }, h('a', { href: r.url, target: '_blank', rel: 'noopener' }, r.source)))))));
}
function initParams(data) {
  const T = data.box && data.box.thickness;
  const rows = [
    ['thickness', `Plywood thickness. Nominal 1/8 in (${T ? T.toFixed(3) : '3.175'} mm); the files come in 0.1 mm steps from 2.8 to 3.5 mm.`],
    ['kerf', 'The width of wood the laser burns away. The generator adds half of it back to every edge so joints come out snug.'],
    ['finger play', `Extra gap in each finger slot so joints close without forcing${data.box && data.box.finger_play ? ': ' + data.box.finger_play + ' mm' : ''}.`],
    ['clearances', 'Gaps that let the drawers and lid slide: the faceplate has 0.75 mm all round in its opening, and the lid has about 1.2 mm of vertical play in its slots.'],
    ['magnet press fit', 'How much smaller the magnet hole is than the magnet: 0.35 mm.'],
    ['box', `${data.box ? `${data.box.length} × ${data.box.width} × ${data.box.height}` : '304.8 × 165.1 × 127'} mm outside.`],
  ];
  const dl = $('#params'); for (const [k, v] of rows) dl.append(h('dt', {}, k), h('dd', {}, v));
}

// ---------- boot ----------
async function boot() {
  initChrome(); renderRules(); initOptions();
  // the cut-file manifest (and the lists that use it) load when the reader gets near them
  const near = new IntersectionObserver(es => { if (!es.some(e => e.isIntersecting)) return; near.disconnect(); initFiles(); initMaterials(); }, { rootMargin: '1200px' });
  for (const id of ['build', 'files', 'materials', 'cutting']) near.observe(document.getElementById(id));
  const ctx = { slots: {}, artState, prerender: /[?&]prerender=1/.test(location.search), reduced: REDUCED };
  const [text, art, renders] = await Promise.all([getText('data/parts.json'), getJSON('data/art-manifest.json'), getJSON('img/render/index.json')]);
  ctx.renders = renders;
  if (!text) { $('#hero-loading').textContent = 'The parts list could not load.'; return; }
  ctx.data = JSON.parse(text); ctx.dataHash = hash(text); ctx.art = art;
  artState.manifest = art;
  initParams(ctx.data);
  renderHow(ctx); renderInventory(ctx); renderJoints(ctx); renderSteps(ctx); initEngraving(ctx);
  // hero still for browsers without WebGL (replaced by the live model when it loads)
  const heroSrc = renderSrc(ctx, 'hero_small') || renderSrc(ctx, 'hero');
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
  const hasGL = (() => { try { const c = document.createElement('canvas'); const g = c.getContext('webgl2') || c.getContext('webgl'); if (!g) return false; const x = g.getExtension('WEBGL_lose_context'); x && x.loseContext(); return true; } catch { return false; } })();
  // still picture under the canvas until the 3D box has its art (also the fallback on context loss)
  if (heroSrc && hasGL) $('#hero-stage').prepend(h('img', { class: 'hero-ph', src: heroSrc, alt: '' }));
  for (const [stageSel] of [['#hero-stage'], ['.engrave-stage']]) {
    const st = $(stageSel);
    st.addEventListener('fax-lost', () => { st.classList.add('lost'); if (stageSel === '#hero-stage' && heroSrc && !st.querySelector('.hero-lost')) st.prepend(h('img', { class: 'hero-lost', src: heroSrc, alt: 'The Fax Machine box' })); });
    st.addEventListener('fax-restored', () => location.reload());
  }
  if (!hasGL) { noGL(); return; }
  try { const m = await import('./render3d.js'); await m.start(ctx); }
  catch (e) { console.warn('3D unavailable:', e && e.message); noGL(); }
}
boot();
