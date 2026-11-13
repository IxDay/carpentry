// Record the geometry buffers and shader uniform values a Sketchfab model's
// WebGL viewer uploads, so tools/import_joint.py can rebuild the mesh offline.
//
// The download API needs an account; the public embed does not. Start a Chrome
// with remote debugging and a logged-out profile, then run:
//
//   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
//     --headless=new --remote-debugging-port=9231 about:blank &
//   node tools/sketchfab_capture.mjs caps <uid> [<uid> ...]
//
// The uid is the last path segment of the model URL. Each capture is a JSON
// blob of buffers, vertex attribs, draw calls, shader sources, uniforms and the
// viewer's scene JSON (positions are quantised; import_joint.py decodes them).
// Node 22+ (global fetch and WebSocket).
import fs from 'fs';
import path from 'path';

const PORT = process.env.PORT || 9231;
const OUT = process.argv[2] || 'caps';
const uids = process.argv.slice(3);
if (!uids.length) { console.error('usage: node sketchfab_capture.mjs OUTDIR UID...'); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });

const hook = String.raw`
(() => {
  if (window.__cap) return;
  const ids = new WeakMap();
  let nextId = 1;
  const idOf = (o) => { if (!o) return 0; if (!ids.has(o)) ids.set(o, nextId++); return ids.get(o); };
  const cap = window.__cap = { buffers: [], attribs: [], draws: [], shaders: [], parses: [], programs: [] };
  const copy = (data) => {
    try {
      if (!data) return null;
      if (data instanceof ArrayBuffer) return Array.from(new Uint8Array(data));
      if (ArrayBuffer.isView(data)) return Array.from(new Uint8Array(data.buffer, data.byteOffset, data.byteLength));
    } catch (e) {}
    return null;
  };
  const wrap = (proto) => {
    if (!proto) return;
    const bb = proto.bindBuffer;
    proto.bindBuffer = function (target, buffer) {
      try { this.__bound = this.__bound || {}; this.__bound[target] = buffer; } catch (e) {}
      return bb.apply(this, arguments);
    };
    const bd = proto.bufferData;
    proto.bufferData = function (target, data, usage) {
      try {
        const bytes = copy(data);
        if (bytes) cap.buffers.push({ target, len: bytes.length, bytes,
          bound: idOf(this.__bound && this.__bound[target]) });
      } catch (e) {}
      return bd.apply(this, arguments);
    };
    const bs = proto.bufferSubData;
    proto.bufferSubData = function (target, offset, data) {
      try {
        const bytes = copy(data);
        if (bytes) cap.buffers.push({ target, len: bytes.length, bytes, sub: offset,
          bound: idOf(this.__bound && this.__bound[target]) });
      } catch (e) {}
      return bs.apply(this, arguments);
    };
    const vap = proto.vertexAttribPointer;
    proto.vertexAttribPointer = function (index, size, type, norm, stride, offset) {
      try { cap.attribs.push({ index, size, type, norm, stride, offset,
        buf: idOf(this.__bound && this.__bound[this.ARRAY_BUFFER]) }); } catch (e) {}
      return vap.apply(this, arguments);
    };
    const ss = proto.shaderSource;
    proto.shaderSource = function (shader, source) {
      try { cap.shaders.push(source); } catch (e) {}
      return ss.apply(this, arguments);
    };
    const lp = proto.linkProgram;
    proto.linkProgram = function (program) {
      try { cap.programs.push({ gl: this, program }); } catch (e) {}
      return lp.apply(this, arguments);
    };
    const de = proto.drawElements;
    proto.drawElements = function (mode, count, type, offset) {
      try {
        const p = this.getParameter(this.CURRENT_PROGRAM);
        cap.draws.push({ mode, count, type, offset,
          elem: idOf(this.__bound && this.__bound[this.ELEMENT_ARRAY_BUFFER]),
          prog: p && (p.__prog = p.__prog || ('p' + (++nextId))) });
      } catch (e) {}
      return de.apply(this, arguments);
    };
  };
  wrap(window.WebGLRenderingContext && WebGLRenderingContext.prototype);
  wrap(window.WebGL2RenderingContext && WebGL2RenderingContext.prototype);
  const jp = JSON.parse;
  JSON.parse = function (text, reviver) {
    const r = jp.call(this, text, reviver);
    try {
      if (r && typeof r === 'object' && (r['osg.Node'] || r.Version !== undefined)) {
        cap.parses.push(JSON.stringify(r));
      }
    } catch (e) {}
    return r;
  };
  window.__dump = () => {
    const uniforms = [];
    for (const { gl, program } of cap.programs) {
      const n = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS) || 0;
      const u = {};
      for (let i = 0; i < n; i++) {
        const info = gl.getActiveUniform(program, i);
        if (!info) continue;
        if (!/^(uQVS|uQVT|uModelMatrix|uModelViewMatrix)$/.test(info.name)) continue;
        try {
          const loc = gl.getUniformLocation(program, info.name);
          if (loc) u[info.name] = Array.from(gl.getUniform(program, loc)).map(x => Math.round(x * 1e6) / 1e6);
        } catch (e) {}
      }
      if (Object.keys(u).length) uniforms.push({ prog: program.__prog, uniforms: u });
    }
    return JSON.stringify(Object.assign({}, cap, { programs: uniforms }));
  };
  window.__ready = () => cap.buffers.length > 0 && cap.draws.length > 0 &&
    cap.shaders.some(s => s.indexOf('uQVS') >= 0);
})();
`;

async function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
const page = list.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0; const pending = new Map();
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
};
const send = (method, params = {}) => new Promise(r => {
  const i = ++id; pending.set(i, r);
  ws.send(JSON.stringify({ id: i, method, params }));
});
await new Promise(r => ws.onopen = r);
await send('Page.enable');
await send('Runtime.enable');
await send('Page.addScriptToEvaluateOnNewDocument', { source: hook });

let failures = 0;
for (const uid of uids) {
  const file = path.join(OUT, uid + '.json');
  if (fs.existsSync(file)) { console.log(uid, 'cached'); continue; }
  await send('Page.navigate', { url: `https://sketchfab.com/models/${uid}/embed?autostart=1&ui_theme=light&tracking=0&ui_infos=0` });
  let ok = false;
  for (let i = 0; i < 30; i++) {
    await wait(1000);
    const r = await send('Runtime.evaluate', { expression: '!!(window.__ready && window.__ready())', returnByValue: true });
    if (r.result && r.result.result && r.result.result.value) { ok = true; break; }
  }
  if (!ok) { console.error(uid, 'timeout'); failures++; continue; }
  await wait(700);
  const r = await send('Runtime.evaluate', { expression: 'window.__dump()', returnByValue: true });
  const val = r.result && r.result.result && r.result.result.value;
  if (!val || val.length < 1000) { console.error(uid, 'empty'); failures++; continue; }
  fs.writeFileSync(file, val);
  const cap = JSON.parse(val);
  const modes = [...new Set(cap.draws.map(d => d.mode + ':' + d.count))].join(' ');
  console.log(uid, 'buffers', cap.buffers.length, 'draws', cap.draws.length, 'shaders',
    cap.shaders.length, 'parses', cap.parses.length, '|', modes);
}
ws.close();
process.exit(failures ? 1 : 0);
