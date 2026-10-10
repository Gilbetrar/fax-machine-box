// Build-guide content that does not need three.js: step wording, extra steps,
// how-it-works cards, hardware icons and small hand-drawn diagrams.

export const stepNumber = (s, i) => s.number ?? s.n ?? s.step ?? s.index ?? (i + 1);
export const stepParts = s => s.parts || s.part_ids || s.added || [];
export const cleanName = n => String(n || '').replace(/\s*\((lower|upper)( drawer)?\)/i, '');

// Site-side wording added to the exporter's steps, keyed by step id.
export const STEP_TEXT = {
  drawer_walls: { title: 'Drawer back and front', note: 'Build both drawers the same way, one at a time. The back is the panel with the round magnet hole{BACK_SIDE}; the front has the grip slot.', tools: ['wood glue'] },
  drawer_left_side: { title: 'Drawer left side', note: 'Engraved face out. Left means the left as you face the front of the box: the COLORS (lower) drawer gets the desert birds on this side, the Lines (upper) drawer gets the gallery.', tools: ['wood glue'] },
  drawer_right_side: { title: 'Drawer right side', note: 'Engraved face out. The COLORS drawer gets the alligator and gull, the Lines drawer the bookshelf. The four corners close together.', tools: ['wood glue'] },
  drawer_bottom: { title: 'Drawer bottom', note: 'Its fingers mesh with the bottom edges of all four walls. This finishes one glue session: let the drawer set for 30 minutes before the faceplate.', tools: ['wood glue'] },
  drawer_face: { title: 'Faceplate', note: 'Engraved face out: COLORS goes on the lower drawer, Lines on the upper one. Line up the two grip slots so a finger reaches through both, center it side to side, and set its bottom edge 0.75 mm above the bottom edge of the drawer body (a strip of thin card makes a good spacer), so it sits evenly in its opening. Clamp. Glue the drawer nowhere else.', tools: ['wood glue', 'clamps'] },
  box_frame: { title: 'Top panel, shelf and divider', note: 'Work on the right wall laid flat, inside face up, so the three parts have something to rest on: hold the top panel and shelf at their slots, slide the divider in, then lower the three onto the wall in the next step. The divider seats in the shelf and top panel any way round, so check it against the walls during the dry fit: its magnet holes face the rear, at drawer height. The top panel goes engraved side up, with the snake toward the front.', tools: ['wood glue'] },
  box_right: { title: 'Right wall', note: 'Engraved face out, lid slot mouth to the front. The two side walls are mirror images: seen from the front, the parrot wall is on the left and the writers’ wall on the right, and both lid slot mouths open at the front. Count the column of divider holes behind the lid slot: the LEFT wall has one more (the cut-files section gives the count for your thickness). Glue session: frame and right wall together. Before the glue sets, check that the frame sits square on the wall and slide a drawer into each bay; then leave it for 30 minutes.', tools: ['wood glue', 'mallet'] },
  box_rear: { title: 'Rear wall', note: 'Hold it by its edges until it is glued; the strip under the lower opening is thin. Use glue sparingly on the joints inside the drawer bay, because you cannot reach in to wipe squeeze-out.', tools: ['wood glue', 'mallet'] },
  box_left: { title: 'Left wall', note: 'Engraved face out, lid slot mouth to the front. Rear and left walls are one glue session. While the glue is still soft, measure the diagonals of the open front and test-slide both drawers through the rear openings.', tools: ['wood glue', 'mallet'] },
  box_front: { title: 'Front wall', note: 'Engraved face out, with the fax screen at the top. Front wall and bottom are the last glue session.', tools: ['wood glue', 'mallet'] },
  box_bottom: { title: 'Bottom panel', note: 'Its plain edge sits against the rear wall.', tools: ['wood glue', 'mallet'] },
  box_lid: { title: 'Sliding lid', note: 'Grip slot toward the front, engraved side up. Slide it over the front wall into both slots until it stops at the divider. Never glue the lid or its slots.' },
  drawers_in: { title: 'Drawers in', note: 'COLORS goes in the lower opening, Lines in the upper one. Nothing stops a drawer from coming all the way out, so support it when you pull it far.' },
};

// Steps the geometry export does not model.
export const EXTRA_STEPS = [
  { before: 'drawer_walls', id: 'prep', title: 'Sort the parts and dry-fit', focus: 'dryfit',
    caption: 'Lay the parts out by letter. Engraved faces always face out; a part with its gray labels showing is inside-out. Parts without art carry small gray joint numbers on their inside face, and two edges with the same number go together; where a plain part meets an art part, only the plain part is numbered. Dry-fit the whole box once without glue, following the steps below, then take it apart and glue it in the same order. Titebond III stays workable for about 10 minutes, so glue in short sessions as the steps say, letting each one set for 30 minutes: a thin line of glue on the fingers, tap the joint home with a mallet or a block of wood, and wipe off what squeezes out.',
    tools: ['wood glue', 'mallet or block of wood', 'damp cloth'] },
  { before: 'drawer_walls', id: 'magnets_drawer', title: 'Magnets: drawer backs', focus: 'magnets_drawer',
    caption: 'Magnets go in while the parts are loose. Snap two magnets together and, without separating them, put a marker dot on both outer faces. Pull them apart. Press one into the hole in a drawer back with its dot facing into the drawer, flush with the outside face; keep its partner for the divider. Do the same for the second drawer. A drop of CA glue holds them if the fit is loose.',
    hardware: ['{MAGNETS} × 6 × 2 mm disc magnet'], tools: ['marker', 'CA glue'] },
  { before: 'box_frame', id: 'magnets_divider', title: 'Magnets: divider', focus: 'magnets_divider',
    caption: 'Press each partner magnet into a divider hole from the rear (drawer) side, dot facing the front, flush with the rear face. The dots face away from each other across the gap, so each pair always attracts.',
    hardware: [], tools: ['CA glue'] },
  { after: 'box_bottom', id: 'square', title: 'Square and clamp', focus: 'square',
    caption: 'Measure both diagonals. When they match, clamp or tape the box for 30 to 60 minutes, and give the glue 24 hours before you load it. Slide each drawer into its opening once while the glue is soft to check the bay is square.',
    tools: ['clamps or painter\'s tape', 'tape measure'] },
  { after: 'drawers_in', id: 'finishing', title: 'Finishing', focus: 'finished',
    caption: 'Sand any scorched edges with 150 grit, then lightly with 220, and wipe off the dust. A finish is optional: if you want one, brush a thin coat of water-based clear finish on the outside only, and keep it off the sliding faces. Rub paraffin or beeswax on the drawer runners and the lid edges so they glide. Lift and carry the box from below, never by the lid or the top front edges: the thin rails above the lid slots break easily.',
    tools: ['150 and 220 grit sandpaper', 'damp cloth', 'paraffin or beeswax'] },
  { after: 'finishing', id: 'paper', title: 'Paper', focus: 'paper',
    caption: 'Cut letter paper into quarters, 4.25 × 5.5 in. Stand a stack on its long edge in the front compartment.',
    hardware: ['letter paper'], tools: ['paper cutter or scissors'] },
];

// round holes (magnets) in a part, in box coordinates of the exporter's frame
function roundHoles(p) {
  const out = []; const t = p.transform; const M = Array.isArray(t[0]) ? t.flat() : t;
  for (const hh of p.holes || []) {
    if (hh.length < 12) continue;
    let cx = 0, cy = 0; for (const [x, y] of hh) { cx += x; cy += y; } cx /= hh.length; cy /= hh.length;
    const r = Math.hypot(hh[0][0] - cx, hh[0][1] - cy); if (r < 2 || r > 4) continue;
    out.push({ x: M[0] * cx + M[1] * cy + M[3], y: M[4] * cx + M[5] * cy + M[7], z: M[8] * cx + M[9] * cy + M[11] });
  }
  return out;
}
// facts the magnet wording depends on, read from parts.json
export function magnetFacts(data) {
  const W = (data.box && data.box.width) || 165.1;
  const leftHanded = String((data.box && data.box.handedness) || '').startsWith('l');
  const backs = data.parts.filter(p => /back/i.test(p.id + ' ' + p.name) && /drawer|^(b|t)_/i.test(p.id + ' ' + p.name));
  const div = data.parts.find(p => /divider/i.test(p.id + p.name));
  const bh = backs.flatMap(roundHoles), dh = div ? roundHoles(div) : [];
  const total = bh.length + dh.length;
  let side = '';
  if (bh.length) {
    const y = bh[0].y, off = y - W / 2;
    if (Math.abs(off) > 5) { const towardRight = leftHanded ? off > 0 : off < 0; side = towardRight ? 'right' : 'left'; }
  }
  return { total: total || 4, side };
}

// The exporter's steps with titles and notes merged in, plus the extra steps.
export function buildSteps(data) {
  const mf = magnetFacts(data);
  const fill = t => String(t || '').replace('{MAGNETS}', mf.total).replace('{BACK_SIDE}', mf.side ? `, which sits off-center: put that end against the drawer's ${mf.side} side, so in the box it lines up with the divider's magnet holes` : '');
  const out = (data.steps || []).map((s, i) => {
    const t = STEP_TEXT[s.id] || {};
    const base = s.caption || s.text || s.description || '';
    return { ...s, n: stepNumber(s, i), title: s.title || t.title || base.split(/[.:]/)[0], caption: fill([base, t.note].filter(Boolean).join(' ')),
      hardware: (s.hardware || t.hardware || []).map(fill), tools: s.tools || t.tools || [], diagram: t.diagram };
  });
  for (const x of EXTRA_STEPS) {
    if (out.some(s => s.id === x.id)) continue;
    let at = out.length;
    if (x.before) { const k = out.findIndex(s => s.id === x.before); if (k >= 0) at = k; }
    if (x.after) { const k = out.findIndex(s => s.id === x.after); if (k >= 0) at = k + 1; }
    const anchor = out[Math.min(at, out.length) - 1];
    out.splice(at, 0, { ...x, caption: fill(x.caption), hardware: (x.hardware || []).map(fill), parts: [], extra: true, upto: anchor ? anchor.n : 0 });
  }
  return out;
}

export const HOW_CARDS = [
  { id: 'paper', title: 'Paper slot', text: 'The front compartment holds a stack of quarter-letter sheets (4.25 × 5.5 in) standing on their long edge. Slide the lid forward, out the front, to take a page.', alt: 'Cutaway of the front compartment holding a stack of paper on edge' },
  { id: 'drawers', title: 'Two drawers with magnet catches', text: 'COLORS holds colored pencils and Lines holds pens. Each drawer pulls out the back. A pair of small magnets, one in the drawer and one in the divider, pulls it shut and keeps it closed when you carry the box.', alt: 'The upper drawer pulled out of the back of the box, with its magnet catch' },
  { id: 'lid', title: 'Sliding lid', text: 'The lid rides in two slots cut into the side walls and slides out the front. It has no lock. The lid rests in its slots and stays closed while the box is level, so carry it level and lift it from below, never by the lid or the top front edges.', alt: 'The sliding lid pulled forward out of its slots' },
  { id: 'joints', title: 'Finger joints', text: 'Every corner is a row of interlocking fingers cut to the exact plywood thickness. They line the box up square on their own, and a little wood glue makes them permanent.', alt: 'A corner of the box pulled apart to show the interlocking finger joints' },
];

export const TOOLS = ['Calipers (to measure the plywood)', 'Wood glue (Titebond III)', 'CA glue for the magnets', 'Clamps', 'Painter\'s tape', 'Damp cloth', 'Small mallet or a block of wood', 'Tape measure', '150 and 220 grit sandpaper', 'Paraffin or beeswax', 'Marker', 'Paper cutter or scissors'];

export const HARDWARE_FALLBACK = [
  { name: 'Disc magnet, 6 × 2 mm', qty: 4, spares: 2 }];

export const HW_ICONS = {
  magnet: '<svg viewBox="0 0 54 54" aria-hidden="true"><ellipse cx="27" cy="33" rx="17" ry="7" fill="#9aa0a8" stroke="#1d1b19" stroke-width="2.4"/><path d="M10 25v8M44 25v8" stroke="#1d1b19" stroke-width="2.4"/><ellipse cx="27" cy="25" rx="17" ry="7" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4"/></svg>',
  bolt: '<svg viewBox="0 0 54 54" aria-hidden="true"><path d="M15 12h24c0 7-5 10-12 10s-12-3-12-10z" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4" stroke-linejoin="round"/><path d="M23 22h8v24h-8z" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4"/><path d="M23 27l8 2M23 32l8 2M23 37l8 2M23 42l8 2" stroke="#1d1b19" stroke-width="1.6"/></svg>',
  nut: '<svg viewBox="0 0 54 54" aria-hidden="true"><path d="M27 9l15 9v18l-15 9-15-9V18z" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4" stroke-linejoin="round"/><circle cx="27" cy="27" r="7" fill="#fff" stroke="#1d1b19" stroke-width="2.4"/><circle cx="27" cy="27" r="10.5" fill="none" stroke="#2f6fc9" stroke-width="2"/></svg>',
  washer: '<svg viewBox="0 0 54 54" aria-hidden="true"><circle cx="27" cy="27" r="16" fill="#d1d5da" stroke="#1d1b19" stroke-width="2.4"/><circle cx="27" cy="27" r="6" fill="#fff" stroke="#1d1b19" stroke-width="2.4"/></svg>',
};
export function hwIcon(name) {
  const n = name.toLowerCase();
  return HW_ICONS[n.includes('magnet') ? 'magnet' : n.includes('nut') ? 'nut' : n.includes('washer') ? 'washer' : 'bolt'];
}

const K = (x, y, s, t) => `<text x="${x}" y="${y}" font-family="Kalam, cursive" font-size="${s}" fill="#1d1b19" stroke="none">${t}</text>`;
export const SVG_PAPER = `<svg viewBox="0 0 900 640" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="A letter sheet cut into four quarters"><g fill="none" stroke="#1d1b19" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" style="filter:url(#wobble)">
<rect x="120" y="70" width="330" height="430" fill="#fff"/><path d="M285 60v450M110 285h350" stroke="#d8423a" stroke-dasharray="18 14"/>
<path d="M300 40l-30 -18M300 40l-30 18" stroke="#d8423a"/>${K(140, 560, 40, 'letter, 8.5 × 11 in')}
<path d="M500 285h80m-24-22l24 22-24 22" stroke-width="6"/>
<rect x="630" y="90" width="165" height="215" fill="#fff"/><rect x="645" y="105" width="165" height="215" fill="#fff"/><rect x="660" y="120" width="165" height="215" fill="#fff"/>
<path d="M660 175h165" /><circle cx="800" cy="145" r="15"/>
${K(610, 400, 40, '4 quarters,')}${K(610, 448, 40, '4.25 × 5.5 in')}</g></svg>`;


// Laser starting points. Filled from published sources; see the citations rendered with the table.
export { LASER } from './laser.js';
