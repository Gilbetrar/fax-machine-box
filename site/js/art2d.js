// 2D helpers shared by the page and the 3D code. No three.js here, so the
// page works when WebGL or the module CDN is unavailable.

// ---------- procedural birch ----------
function rand(seed) { let x = seed >>> 0 || 1; return () => ((x = (x * 1664525 + 1013904223) >>> 0) / 4294967296); }
export function birchCanvas(w = 1024, h = 1024, seed = 7) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d'); const r = rand(seed);
  const grd = g.createLinearGradient(0, 0, w, h);
  grd.addColorStop(0, '#efdcb8'); grd.addColorStop(0.5, '#e9d3aa'); grd.addColorStop(1, '#eed9b3');
  g.fillStyle = grd; g.fillRect(0, 0, w, h);
  // soft figure
  for (let i = 0; i < 18; i++) {
    const x = r() * w, y = r() * h, rad = 60 + r() * 220;
    const rg = g.createRadialGradient(x, y, 0, x, y, rad);
    const a = 0.05 + r() * 0.06;
    rg.addColorStop(0, `rgba(196,150,96,${a})`); rg.addColorStop(1, 'rgba(196,150,96,0)');
    g.fillStyle = rg; g.fillRect(0, 0, w, h);
  }
  // grain lines run along x
  for (let i = 0; i < 260; i++) {
    let y = r() * h; const amp = 2 + r() * 10, f = 0.002 + r() * 0.006, ph = r() * 6.28;
    g.beginPath();
    for (let x = -10; x <= w + 10; x += 8) {
      const yy = y + Math.sin(x * f + ph) * amp + Math.sin(x * f * 3.1 + ph) * amp * 0.25;
      x < 0 ? g.moveTo(x, yy) : g.lineTo(x, yy);
    }
    g.strokeStyle = `rgba(150,105,60,${0.04 + r() * 0.09})`;
    g.lineWidth = 0.6 + r() * 1.8; g.stroke();
  }
  return c;
}

// ---------- art (ink) textures ----------
const imgCache = new Map();
export function loadImage(url) {
  if (imgCache.has(url)) return imgCache.get(url);
  const p = new Promise((res, rej) => { const im = new Image(); im.crossOrigin = 'anonymous'; im.onload = () => res(im); im.onerror = () => rej(new Error('image ' + url)); im.src = url; });
  imgCache.set(url, p); return p;
}
export function artUrl(v) {
  const p = v.png || v.svg || v.url;
  if (!p) return null;
  if (/^(https?:|\/|data:)/.test(p)) return p;
  if (p.startsWith('art/')) return p;
  return 'art/' + p.split('/').pop();
}
// Ink canvas: luminance -> alpha in a single colour. pad keeps the edges transparent.
export const PAD = 4;
const inkCache = new Map();
export async function inkCanvas(url, rgb = [62, 36, 18], maxA = 0.92, maxW = 2048) {
  const key = url + rgb.join(',') + maxA;
  if (inkCache.has(key)) return inkCache.get(key);
  const im = await loadImage(url);
  let w = im.naturalWidth || 2000, h = im.naturalHeight || 1000;
  const s = Math.min(1, maxW / Math.max(w, h)); w = Math.round(w * s); h = Math.round(h * s);
  const c = document.createElement('canvas'); c.width = w + 2 * PAD; c.height = h + 2 * PAD;
  const g = c.getContext('2d', { willReadFrequently: true });
  g.drawImage(im, PAD, PAD, w, h);
  const d = g.getImageData(0, 0, c.width, c.height); const a = d.data;
  for (let i = 0; i < a.length; i += 4) {
    const lum = (a[i] * 0.3 + a[i + 1] * 0.59 + a[i + 2] * 0.11) / 255;
    const ink = (1 - lum) * (a[i + 3] / 255);
    a[i] = rgb[0]; a[i + 1] = rgb[1]; a[i + 2] = rgb[2]; a[i + 3] = Math.round(255 * maxA * Math.min(1, ink * 1.15));
  }
  g.putImageData(d, 0, 0);
  inkCache.set(key, c); return c;
}

