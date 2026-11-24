// Headless DOM harness: run the page's inline script against a minimal fake DOM
// and assert that the orig/gt/pred tabs actually rebind the big image.
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(
  path.join(__dirname, '..', 'web', 'index.html'), 'utf8');

// ---- minimal fake DOM ---------------------------------------------------
class El {
  constructor(tag) {
    this.tagName = String(tag).toUpperCase();
    this.children = [];
    this.dataset = {};
    this.style = {};
    this._cls = new Set();
    this.src = '';
    this.title = '';
    this.innerHTML = '';
    this.onclick = null;
    this.classList = {
      add: (c) => this._cls.add(c),
      remove: (c) => this._cls.delete(c),
      contains: (c) => this._cls.has(c),
      toggle: (c, force) => {
        const on = force === undefined ? !this._cls.has(c) : !!force;
        if (on) this._cls.add(c); else this._cls.delete(c);
        return on;
      },
    };
  }
  appendChild(c) { this.children.push(c); return c; }
  scrollIntoView() {}
}

const byId = new Map();
function mk(tag, id) {
  const e = new El(tag);
  if (id) { byId.set(id, e); }
  return e;
}

// tabs containers + their buttons, parsed from the real markup
const tabsRe = /<div class="tabs" id="(tabs\d*)">([\s\S]*?)<\/div>/g;
let m;
while ((m = tabsRe.exec(html))) {
  const box = mk('div', m[1]);
  const btnRe = /data-mode="(\w+)"([^>]*)>([^<]*)</g;
  let b;
  while ((b = btnRe.exec(m[2]))) {
    const btn = mk('button', null);
    btn.dataset.mode = b[1];
    btn.textContent = b[3];
    btn.className = b[2].includes('class="on"') ? 'on' : '';
    if (b[2].includes('class="on"')) btn._cls.add('on');
    box.appendChild(btn);
  }
}

['big'].forEach((id) => mk('img', id));
['meta'].forEach((id) => mk('div', id));
['thumbs'].forEach((id) => mk('div', id));

const keyHandlers = [];
const document = {
  getElementById: (id) => byId.get(id) || null,
  createElement: (tag) => new El(tag),
  querySelectorAll: (sel) => {
    const mm = /^#(\w+) button$/.exec(sel);
    if (!mm) return [];
    const box = byId.get(mm[1]);
    return box ? box.children.filter((c) => c.tagName === 'BUTTON') : [];
  },
  addEventListener: (type, fn) => { if (type === 'keydown') keyHandlers.push(fn); },
};

// ---- run the page script ------------------------------------------------
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((x) => x[1]);
if (!scripts.length) { console.log('FAIL: no inline script'); process.exit(1); }
const code = scripts[scripts.length - 1];

const sandbox = { document, console, Object, Array, String, Number, Math };
try {
  new Function('document', 'console', code)(document, console);
} catch (e) {
  console.log('FAIL: script threw:', e.message);
  process.exit(1);
}

// ---- assertions ---------------------------------------------------------
let fails = 0;
function check(name, cond, extra) {
  if (!cond) { fails++; console.log('FAIL ', name, extra === undefined ? '' : extra); }
  else { console.log('ok   ', name, extra === undefined ? '' : extra); }
}

for (const [tabId, bigId, thumbId] of [['tabs', 'big', 'thumbs']]) {
  const box = byId.get(tabId);
  const big = byId.get(bigId);
  const thumbs = byId.get(thumbId);

  check(tabId + ' has 3 buttons', box.children.length === 3, box.children.length);
  check(thumbId + ' got thumbnails', thumbs.children.length > 0, thumbs.children.length);
  check(tabId + ' buttons bound', box.children.every((b) => typeof b.onclick === 'function'));

  const initial = big.src;
  check(bigId + ' initial src is orig', /\/orig_/.test(initial), initial.split('/').pop());

  const gtBtn = box.children.find((b) => b.dataset.mode === 'gt');
  const predBtn = box.children.find((b) => b.dataset.mode === 'pred');
  const origBtn = box.children.find((b) => b.dataset.mode === 'orig');

  gtBtn.onclick();
  const gtSrc = big.src;
  check(bigId + ' click 真值 switches to gt', /\/gt_/.test(gtSrc) && gtSrc !== initial, gtSrc.split('/').pop());

  predBtn.onclick();
  const predSrc = big.src;
  check(bigId + ' click 模型预测 switches to pred', /\/pred_/.test(predSrc), predSrc.split('/').pop());

  origBtn.onclick();
  check(bigId + ' click 原图 back to orig', /\/orig_/.test(big.src), big.src.split('/').pop());

  check(tabId + ' active button class tracked',
    box.children.filter((b) => b._cls.has('on')).length === 1);

  check(bigId + ' meta shows page marker', /\/\s*\d+\s*\/\s*\d+/.test(byId.get('meta').innerHTML) ||
      /\d+ \/ \d+/.test(byId.get('meta').innerHTML));
}

// keyboard wrap-around on the active gallery
const big = byId.get('big');
const thumbs = byId.get('thumbs');
const firstThumb = thumbs.children[0];
firstThumb.onclick();                       // focus gallery 1, index 0
const src0 = big.src;
keyHandlers.forEach((h) => h({ key: 'ArrowLeft', preventDefault() {} }));   // wrap to last
check('ArrowLeft wraps to last image', big.src !== src0, big.src.split('/').pop());
keyHandlers.forEach((h) => h({ key: 'ArrowRight', preventDefault() {} }));  // wrap back to first
check('ArrowRight wraps back to first', big.src === src0);

console.log(fails ? 'RESULT: ' + fails + ' failure(s)' : 'RESULT: all checks passed');
process.exit(fails ? 1 : 0);
