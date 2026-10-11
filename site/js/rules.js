// Ben's eight-panel rules card, redrawn. Each panel is a small hand-drawn SVG.
const S = 'fill="none" stroke="#1d1b19" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"';
const T = (x, y, s, txt, extra = '') => `<text x="${x}" y="${y}" font-family="Kalam, cursive" font-weight="700" font-size="${s}" fill="#1d1b19" ${extra}>${txt}</text>`;
const page = (x, y, w, hh, fill = '#fff') => `<rect x="${x}" y="${y}" width="${w}" height="${hh}" rx="2" fill="${fill}" ${S}/>`;
const circ = (x, y, n, r = 10) => `<circle cx="${x}" cy="${y}" r="${r}" ${S} stroke-width="2.4" fill="#fff"/>${T(x - 4, y + 5.5, 15, n)}`;
const squig = (x, y, w) => `<path d="M${x} ${y} q6 -5 12 0 t12 0 t12 0 t12 0 t12 0${w > 60 ? ' t12 0' : ''}" ${S} stroke-width="2.2"/>`;
const stack = (x, y, w, hh, n = 4, top = '') => {
  let o = '';
  for (let i = n - 1; i >= 0; i--) o += page(x + i * 9, y - i * 7, w, hh);
  return o + top;
};
const arrow = (x1, y1, x2, y2, col = '#d8423a') =>
  `<path d="M${x1} ${y1} Q ${(x1 + x2) / 2} ${Math.min(y1, y2) - 34} ${x2} ${y2}" fill="none" stroke="${col}" stroke-width="3.4" stroke-linecap="round"/>` +
  `<path d="M${x2 - 13} ${y2 - 9} L${x2 + 2} ${y2 + 1} L${x2 - 12} ${y2 + 8}" fill="${col}" stroke="${col}" stroke-width="3" stroke-linejoin="round"/>`;
const duck = (x, y, s) => `<use href="#duck-art" x="${x}" y="${y}" width="${s}" height="${s * 1.1}"/>`;
const wrap = inner => `<svg viewBox="0 0 240 170" xmlns="http://www.w3.org/2000/svg" role="img">${inner}</svg>`;

export const RULES = [
  { title: 'Number papers', text: 'Everyone takes four quarter-sheets and numbers them 1 to 4 in the top-right corner.',
    svg: wrap([0, 1, 2, 3].map(i => page(16 + i * 56, 56, 42, 56) + T(44 + i * 56, 76, 15, i + 1)).join('')) },
  { title: 'Write something', text: 'Write a phrase in the top band of page 1.',
    svg: wrap(page(58, 12, 124, 150) + `<path d="M58 56 H182" ${S}/>` + T(66, 32, 15, 'A duck with') + T(66, 49, 15, 'a cool hat.') + circ(164, 28, 1) +
      `<path d="M150 98 l18 -22 6 6 -18 22 -8 2z" fill="#f6d33c" ${S} stroke-width="2.4"/>`) },
  { title: 'Pass the whole stack', text: 'Everyone hands their whole stack, all four pages, to the next player. Always pass in the same direction.',
    svg: wrap(stack(24, 82, 56, 70) + arrow(120, 82, 204, 96)) },
  { title: 'Draw', text: 'Draw the phrase in the space under the words.',
    svg: wrap(page(58, 8, 124, 156) + `<path d="M58 44 H182" ${S}/>` + squig(66, 22, 66) + squig(66, 34, 54) + circ(166, 24, 1) + duck(84, 50, 82)) },
  { title: 'Fold and hide words', text: 'Fold the words backward, behind the page, so only your drawing shows.',
    svg: wrap(`<path d="M74 40 L166 40 L160 22 L80 22 Z" fill="#efe9dc" stroke="#9a9186" stroke-width="2.4" stroke-dasharray="5 5" stroke-linejoin="round"/>` +
      page(66, 40, 108, 120) + duck(80, 52, 78) + arrow(136, 38, 196, 54)) },
  { title: 'Pass the whole stack', text: 'Pass the whole stack to the next player.',
    svg: wrap(stack(26, 76, 64, 80, 4, duck(34, 80, 50)) + arrow(132, 70, 210, 86)) },
  { title: 'Write it', text: 'Look at the drawing and write what you think it is in the top band of page 2.',
    svg: wrap(page(16, 32, 86, 108) + duck(24, 42, 70) + T(110, 96, 30, '=') +
      page(138, 32, 92, 108) + `<path d="M138 66 H230" ${S}/>` + T(144, 50, 12.5, 'A goose in') + T(144, 62, 12.5, 'a cap') + circ(216, 46, 2, 9)) },
  { title: 'Hide drawing, pass full stack', text: 'Turn page 1 face down and put it at the back of the stack, so page 2, with the new words, is on top. Pass the whole stack.',
    svg: wrap(stack(26, 76, 64, 80, 4, `<path d="M26 104 H90" ${S}/>` + squig(32, 88, 36) + circ(78, 90, 2, 8)) + arrow(132, 70, 210, 86)) },
];
