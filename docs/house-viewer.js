/* Interactive house viewer for the third site tab.
 *
 * The house GLB is one mesh per timber.  This element loads it with three.js,
 * raycasts the timbers, and reads house/connections.json for the joint
 * instances cut into them.  A hovered timber outlines and marks its
 * connections; a hovered or pinned connection ghosts everything else and shows
 * a link straight to the matching catalog specimen.
 *
 * It is a custom element on purpose: the page can lazy-import this module when
 * the house tab is first opened, and <model-viewer> stays untouched for the 53
 * joint specimens.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

// A focused house joint is written to the URL as an anchor so a reader can
// follow the card's catalog link and come back to the exact view with the
// browser's Back button (or a reload/bookmark).  The syntax is owned here; the
// site template only needs to know that "#house/…" selects the house tab.
const VIEW_HASH = /^#house\/([^?]+)(?:\?(.*))?$/;
const isViewHash = hash => VIEW_HASH.test(hash || '');
const triple = (value) => {
  if (!value) return null;
  const parts = value.split(',').map(Number);
  return parts.length === 3 && parts.every(Number.isFinite) ? parts : null;
};
const round2 = value => String(Math.round(value * 100) / 100);

const TEMPLATE = `
<style>
  :host {
    --hv-paper: var(--paper, #1c1916);
    --hv-card: var(--card, #25211d);
    --hv-ink: var(--ink, #efe6d6);
    --hv-muted: var(--muted, #a39a8c);
    --hv-line: var(--line, #38322b);
    --hv-accent: var(--accent, #e0765a);
    --hv-jp: var(--jp, #8d857a);
    display: block;
    position: relative;
    width: 100%;
    height: min(62vh, 34rem);
    color: var(--hv-ink);
    font: 13px/1.45 system-ui, -apple-system, "Segoe UI", "Hiragino Sans",
      "Noto Sans JP", sans-serif;
    -webkit-tap-highlight-color: transparent;
  }
  :host(:focus-visible) { outline: 2px solid var(--hv-accent); outline-offset: -2px; }
  [hidden] { display: none !important; }
  canvas {
    position: absolute; inset: 0; width: 100%; height: 100%;
    display: block; touch-action: pan-y; cursor: grab;
  }
  .loading {
    position: absolute; z-index: 3; left: 0; right: 0; bottom: 4.2rem;
    text-align: center; color: var(--hv-muted); pointer-events: none;
    font-size: .8rem; letter-spacing: .02em;
  }
  .bar {
    position: absolute; z-index: 6; left: .7rem; bottom: .7rem;
    display: flex; gap: .35rem; align-items: center; flex-wrap: wrap;
  }
  .peel {
    display: flex; overflow: hidden; border: 1px solid var(--hv-line);
    border-radius: 999px; background: var(--hv-paper);
  }
  .peel button { border: 0; border-radius: 0; border-right: 1px solid var(--hv-line); padding: .3rem .52rem; }
  .peel button:last-child { border-right: 0; }
  button {
    font: inherit; color: var(--hv-ink); background: var(--hv-paper);
    border: 1px solid var(--hv-line); border-radius: 999px;
    padding: .3rem .72rem; cursor: pointer; line-height: 1.2;
  }
  button:hover { border-color: var(--hv-accent); }
  button[aria-pressed="true"], button.on {
    background: var(--hv-accent); border-color: var(--hv-accent); color: #1c1916;
  }
  button:focus-visible, a:focus-visible {
    outline: 2px solid var(--hv-accent); outline-offset: 2px;
  }
  .info {
    position: absolute; z-index: 7; left: .7rem; top: .7rem;
    width: min(21rem, calc(100% - 1.4rem)); max-height: min(62%, 24rem);
    overflow: auto; padding: .7rem .82rem;
    background: var(--hv-card);
    border: 1px solid var(--hv-line); border-radius: 8px;
    box-shadow: 0 8px 28px rgba(0, 0, 0, .32);
    pointer-events: auto;
  }
  .info h3 {
    margin: 0; font: 600 .98rem/1.25 Georgia, "Iowan Old Style", serif;
    display: flex; gap: .4rem; align-items: baseline; flex-wrap: wrap;
  }
  .info .jp { color: var(--hv-jp); font-size: .8rem; letter-spacing: .05em; }
  .info .sub { display: block; color: var(--hv-muted); font-size: .76rem; margin-top: .12rem; }
  .info p { margin: .45rem 0 .35rem; }
  .info .desc { color: var(--hv-ink); }
  .info .members { color: var(--hv-muted); font-size: .78rem; }
  .info .links { display: flex; flex-wrap: wrap; gap: .35rem .7rem; margin-top: .45rem; }
  .info a { color: var(--hv-accent); }
  .info .badge {
    display: inline-block; padding: .05rem .4rem; border: 1px solid var(--hv-line);
    border-radius: 999px; font-size: .66rem; letter-spacing: .05em;
    text-transform: uppercase; color: var(--hv-muted);
  }
  .info .badge.pinned { border-color: var(--hv-accent); color: var(--hv-accent); }
  .info .titles { display: flex; flex-wrap: wrap; gap: .3rem; margin: .4rem 0 0; padding: 0; list-style: none; }
  .info .titles li { display: block; }
  .info .titles button {
    font-size: .74rem; padding: .12rem .45rem; border-radius: 999px;
    background: var(--hv-paper); border: 1px solid var(--hv-line);
    color: var(--hv-muted);
  }
  .info .titles button:hover { border-color: var(--hv-accent); color: var(--hv-ink); }
  .info .clear { margin-top: .5rem; padding: .18rem .55rem; font-size: .75rem; }
  .browser {
    position: absolute; z-index: 9; right: .7rem; top: .7rem; bottom: 3.4rem;
    width: min(23rem, calc(100% - 1.4rem));
    display: flex; flex-direction: column;
    background: var(--hv-card); border: 1px solid var(--hv-line);
    border-radius: 8px; box-shadow: 0 10px 32px rgba(0, 0, 0, .4);
    overflow: hidden;
  }
  .browser header {
    display: flex; gap: .4rem; align-items: center;
    padding: .5rem .55rem; border-bottom: 1px solid var(--hv-line);
  }
  .browser header strong { flex: 0 0 auto; font-size: .82rem; }
  .browser input {
    flex: 1 1 auto; min-width: 0; font: inherit; font-size: .8rem;
    color: var(--hv-ink); background: var(--hv-paper);
    border: 1px solid var(--hv-line); border-radius: 5px; padding: .25rem .45rem;
  }
  .browser .close { padding: .12rem .45rem; border-radius: 5px; }
  .browser .list { overflow: auto; padding: .2rem .45rem .8rem; }
  .browser h4 {
    margin: .7rem 0 .2rem; font: 600 .78rem/1.3 system-ui, sans-serif;
    color: var(--hv-muted); letter-spacing: .03em;
  }
  .browser h4 span { color: var(--hv-jp); font-weight: 400; }
  .browser ul { list-style: none; margin: 0; padding: 0; }
  .browser li button {
    display: block; width: 100%; text-align: left;
    padding: .22rem .35rem; border: 0; border-radius: 4px;
    background: none; color: var(--hv-ink); font-size: .78rem;
  }
  .browser li button:hover { background: var(--hv-paper); }
  .browser li button[aria-current="true"] {
    background: var(--hv-paper); color: var(--hv-accent);
  }
  .browser .empty { color: var(--hv-muted); font-size: .8rem; padding: .8rem .35rem; }
  .error {
    position: absolute; inset: 0; z-index: 10;
    display: grid; grid-auto-rows: max-content;
    place-content: center; gap: .6rem; padding: 2rem;
    text-align: center; background: var(--hv-paper);
  }
  .error img {
    width: min(60%, 16rem); height: auto; max-height: 34vh;
    object-fit: contain; border-radius: 6px; justify-self: center;
  }
  .error h3 { margin: 0; font: 600 1rem/1.3 Georgia, serif; }
  .error p { margin: 0; color: var(--hv-muted); font-size: .82rem; }
  .error a { color: var(--hv-accent); }
  .sr {
    position: absolute; width: 1px; height: 1px; overflow: hidden;
    clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap;
  }
  @media (max-width: 56rem) {
    :host { height: 100%; }
    .bar { left: .6rem; bottom: calc(3.4rem + env(safe-area-inset-bottom)); right: .6rem; }
    .info {
      top: auto; left: .6rem; right: .6rem; bottom: calc(7.2rem + env(safe-area-inset-bottom));
      width: auto; max-height: 40%;
    }
    .browser {
      inset: 4.4rem .6rem calc(3.4rem + env(safe-area-inset-bottom)) .6rem;
      width: auto;
    }
    .loading { bottom: 7rem; }
  }
</style>
<canvas aria-hidden="true"></canvas>
<div class="loading">Loading the house…</div>
<section class="info" hidden></section>
<div class="bar">
  <button type="button" data-play>Play</button>
  <div class="peel" role="group" aria-label="Peel away layers">
    <button type="button" data-peel="solid" aria-pressed="true">Solid</button>
    <button type="button" data-peel="roof" aria-pressed="false">Roof</button>
    <button type="button" data-peel="upper" aria-pressed="false">Upper</button>
    <button type="button" data-peel="frame" aria-pressed="false">Frame</button>
  </div>
  <button type="button" data-browse aria-expanded="false">Browse</button>
</div>
<div class="browser" hidden role="dialog" aria-label="Connection index">
  <header>
    <strong>Connections</strong>
    <input type="search" placeholder="Filter connections" aria-label="Filter connections" autocomplete="off" spellcheck="false">
    <button type="button" class="close" aria-label="Close connection index">×</button>
  </header>
  <div class="list"></div>
</div>
<div class="error" hidden></div>
<div class="sr" role="status" aria-live="polite"></div>
`;

const escapeHtml = (value) => String(value)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

class HouseViewer extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = TEMPLATE;
    this._canvas = this.shadowRoot.querySelector('canvas');
    this._loadingEl = this.shadowRoot.querySelector('.loading');
    this._info = this.shadowRoot.querySelector('.info');
    this._playBtn = this.shadowRoot.querySelector('[data-play]');
    this._peelBtns = [...this.shadowRoot.querySelectorAll('[data-peel]')];
    this._browseBtn = this.shadowRoot.querySelector('[data-browse]');
    this._browser = this.shadowRoot.querySelector('.browser');
    this._browserList = this.shadowRoot.querySelector('.browser .list');
    this._browserSearch = this.shadowRoot.querySelector('.browser input');
    this._browserClose = this.shadowRoot.querySelector('.browser .close');
    this._error = this.shadowRoot.querySelector('.error');
    this._live = this.shadowRoot.querySelector('.sr');

    this._booted = false;
    this._ok = false;
    this._visible = false;
    this._loaded = false;
    this._loading = false;
    this._playing = false;
    this._peel = 'solid';
    this._hoveredPiece = null;
    this._hoveredConnection = null;
    this._focusedConnection = null;
    this._pinnedPiece = null;
    this._markerPiece = null;
    this._markers = [];
    this._markerSprites = [];
    this._outlines = new Map();
    this._lastPointer = null;
    this._lastInfoKey = '';
    this._clock = new THREE.Clock();
    this._raycaster = new THREE.Raycaster();
    this._tmp = new THREE.Vector3();
    this._browserBuilt = false;
    this._clipDuration = 0;
    this._pendingTime = 0;
    this._pulseUntil = 0;
    this._pendingHash = null;
  }

  connectedCallback() {
    if (this._booted) return;
    this._booted = true;
    this._stage = this.closest('.stage');
    this.tabIndex = 0;
    this.setAttribute('role', 'group');
    this.setAttribute('aria-label',
      'Interactive house frame. Drag to orbit. Hover or tap a timber to see its connections, then a joint marker for the detail.');
    this._bindUI();
    this._observe();
    this._initThree();
    if (this._ok) this._load();
  }

  disconnectedCallback() {
    this._stopLoop();
    this._io?.disconnect();
    this._ro?.disconnect();
    document.removeEventListener('visibilitychange', this._onVisibility);
  }

  // -- public API, compatible with the page's Replay handler ---------------
  get currentTime() {
    return this._action ? this._action.time : this._pendingTime;
  }

  set currentTime(value) {
    const time = Math.max(0, Math.min(this._clipDuration || 0,
      Number(value) || 0));
    this._pendingTime = time;
    if (!this._action) return;
    this._action.time = time;
    this._mixer?.update(0);
    this._updateMarkerPositions();
    this._wake();
  }

  play() {
    if (!this._action || this._playing) return;
    if (this._action.time >= this._clipDuration - 0.001) this.currentTime = 0;
    this._clearFocus({ rehover: false });
    this._action.paused = false;
    this._action.play();
    this._playing = true;
    this._updatePlayButton();
    this._buildMarkers();
    this._updateInfo();
    this._wake();
  }

  pause() {
    if (!this._action || !this._playing) return;
    this._action.paused = true;
    this._playing = false;
    this._updatePlayButton();
    this._buildMarkers();
    this._updateInfo();
    this._wake();
  }

  togglePlay() {
    if (this._playing) this.pause();
    else this.play();
  }

  // -- setup --------------------------------------------------------------
  _bindUI() {
    this._playBtn.addEventListener('click', () => this.togglePlay());
    this._peelBtns.forEach(btn => btn.addEventListener('click', () => {
      this._setPeel(btn.dataset.peel);
    }));
    this._browseBtn.addEventListener('click', () => {
      this._toggleBrowser(this._browser.hidden);
    });
    this._browserClose.addEventListener('click', () => this._toggleBrowser(false));
    this._browserSearch.addEventListener('input', () => this._filterBrowser());
    this._browserList.addEventListener('click', (event) => {
      const button = event.target.closest('button[data-connection]');
      if (!button) return;
      const conn = this._connById?.get(button.dataset.connection);
      if (!conn) return;
      this._focus(conn);
      if (matchMedia('(max-width: 56rem)').matches) this._toggleBrowser(false);
    });

    this._info.addEventListener('click', (event) => {
      if (event.target.closest('[data-clear]')) {
        this._clearFocus();
        return;
      }
      const button = event.target.closest('button[data-connection]');
      if (button) {
        const conn = this._connById?.get(button.dataset.connection);
        if (conn) this._focus(conn);
      }
    });

    this.addEventListener('keydown', (event) => {
      // Events from the shadow tree are retargeted to the host, so use the
      // composed path to tell a keystroke on the host from one in a control.
      const target = event.composedPath()[0];
      const typing = target instanceof Element
        && target.closest('input, textarea, select, [contenteditable]');
      if (event.key === 'Escape') {
        if (!this._browser.hidden) this._toggleBrowser(false);
        else this._clearFocus();
        return;
      }
      if (typing) {
        // Keep the page's arrow-key paging and "/" search shortcuts out of the
        // connection filter. The viewer itself does not use arrow keys.
        event.stopPropagation();
        return;
      }
      if (target !== this) return;
      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault();
        this.togglePlay();
      } else if (event.key === 'r' || event.key === 'R') {
        event.preventDefault();
        this.currentTime = 0;
        this.play();
      }
    });

    this._canvas.addEventListener('pointermove', (event) => {
      if (event.pointerType === 'touch') return;
      this._lastPointer = { x: event.clientX, y: event.clientY };
      this._hoverAt(event.clientX, event.clientY);
    });
    this._canvas.addEventListener('pointerleave', (event) => {
      const to = event.relatedTarget;
      if (to && this.shadowRoot.contains(to)) return;
      this._clearHoverSoon();
    });
    this._canvas.addEventListener('pointerdown', (event) => {
      this._down = {
        x: event.clientX, y: event.clientY,
        time: performance.now(), button: event.button,
      };
    });
    this._canvas.addEventListener('pointerup', (event) => {
      const down = this._down;
      this._down = null;
      if (!down || down.button !== 0) return;
      if (Math.hypot(event.clientX - down.x, event.clientY - down.y) > 7) return;
      if (performance.now() - down.time > 800) return;
      this._clickAt(event.clientX, event.clientY);
    });
    // Do not clear the model hover when the pointer goes to one of the
    // overlaid controls; the gesture is about to click something in them.
    for (const el of [this._info, this.shadowRoot.querySelector('.bar'),
      this._browser]) {
      el.addEventListener('pointerenter', () => {
        clearTimeout(this._clearTimer);
      });
      el.addEventListener('pointerleave', () => this._clearHoverSoon());
    }
  }

  _observe() {
    this._io = new IntersectionObserver(entries => {
      const visible = entries.some(entry => entry.isIntersecting);
      this._visible = visible;
      if (visible) {
        this._resize();
        this._wake();
      } else {
        this._stopLoop();
      }
    }, { rootMargin: '220px 0px' });
    this._io.observe(this);
    this._ro = new ResizeObserver(() => {
      if (!this._visible) return;
      this._resize();
      this._wake();
    });
    this._ro.observe(this);
    this._onVisibility = () => {
      if (document.hidden) this._stopLoop();
      else if (this._visible) this._wake();
    };
    document.addEventListener('visibilitychange', this._onVisibility);
  }

  _initThree() {
    if (!this._hasWebGL()) {
      this._showError('This browser cannot start WebGL, so the interactive frame is unavailable.');
      return;
    }
    try {
      this._renderer = new THREE.WebGLRenderer({
        canvas: this._canvas, antialias: true, alpha: true,
        powerPreference: 'high-performance',
      });
      this._renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
      this._renderer.setClearColor(0x000000, 0);
      this._renderer.outputColorSpace = THREE.SRGBColorSpace;
      this._scene = new THREE.Scene();
      this._camera = new THREE.PerspectiveCamera(35, 1, 0.08, 120);
      this._camera.position.set(9, 8, 10);
      this._controls = new OrbitControls(this._camera, this._canvas);
      this._controls.enableDamping = true;
      this._controls.dampingFactor = 0.08;
      this._controls.enablePan = true;
      this._controls.target.set(0, 3.45, 0);
      this._controls.minDistance = 4;
      this._controls.maxDistance = 32;
      this._controls.maxPolarAngle = Math.PI * 0.495;
      this._controls.addEventListener('start', () => {
        this._userMoved = true;
        this._wake();
      });
      this._controls.addEventListener('end', () => this._wake());
      this._controls.update();
      this._ok = true;
      this._resize();
    } catch (error) {
      console.error(error);
      this._showError('This browser could not create a WebGL context.');
    }
  }

  _hasWebGL() {
    try {
      const canvas = document.createElement('canvas');
      return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'));
    } catch {
      return false;
    }
  }

  async _load() {
    if (this._loading) return;
    this._loading = true;
    const src = this.dataset.src;
    const metaSrc = this.dataset.meta;
    if (!src || !metaSrc) {
      this._loading = false;
      this._showError('The house viewer is missing its model or connection data.');
      return;
    }
    try {
      const [gltf, meta] = await Promise.all([
        new GLTFLoader().loadAsync(src),
        fetch(metaSrc).then(response => {
          if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
          return response.json();
        }),
      ]);
      this._setup(gltf, meta);
      this._loading = false;
      if (!this._ok) return;
      this._loaded = true;
      const pending = this._pendingHash;
      this._pendingHash = null;
      if (pending) this.restoreFromHash(pending);
      this._loadingEl.setAttribute('hidden', '');
      this._stage?.classList.add('ready');
      this.dispatchEvent(new Event('load'));
      this._wake();
    } catch (error) {
      console.error(error);
      this._loading = false;
      this._showError('The house model could not be loaded.');
    }
  }

  _setup(gltf, meta) {
    this._meta = meta;
    this._house = meta.house;
    this._levels = meta.house.levels || {};
    this._pieces = meta.pieces;

    const scene = this._scene;
    scene.add(gltf.scene);
    gltf.scene.updateMatrixWorld(true);

    const meshes = [];
    const byId = new Map();
    gltf.scene.traverse(object => {
      if (!object.isMesh) return;
      let id = object.name;
      if (!this._pieces[id] && object.parent) id = object.parent.name;
      const piece = this._pieces[id];
      if (!piece) {
        console.warn('house mesh without metadata:', object.name);
        return;
      }
      object.userData.pieceId = id;
      meshes.push(object);
      byId.set(id, object);
    });
    this._meshes = meshes;
    this._meshById = byId;

    if (!meshes.length) {
      this._showError('The house model contained no timber meshes.');
      return;
    }

    const sourceMaterial = meshes[0].material;
    sourceMaterial.transparent = false;
    sourceMaterial.opacity = 1;
    sourceMaterial.depthWrite = true;
    this._solidMaterial = sourceMaterial;
    this._ghostMaterial = sourceMaterial.clone();
    this._ghostMaterial.transparent = true;
    this._ghostMaterial.opacity = 0.13;
    this._ghostMaterial.depthWrite = false;
    this._ghostMaterial.side = THREE.DoubleSide;
    this._focusMaterial = sourceMaterial.clone();
    this._focusMaterial.color.setRGB(1.34, 1.12, 0.82);
    this._outlineMaterial = new THREE.LineBasicMaterial({
      color: 0xffb589, transparent: true, opacity: 0.95,
      depthTest: false, depthWrite: false,
    });
    meshes.forEach(mesh => { mesh.material = this._solidMaterial; });

    this._markerTexture = this._makeMarkerTexture();
    this._markerMaterial = new THREE.SpriteMaterial({
      map: this._markerTexture, transparent: true, depthTest: false,
      depthWrite: false, color: 0xffb682,
    });
    this._markerActiveMaterial = this._markerMaterial.clone();
    this._markerActiveMaterial.color.set(0xfff0d8);

    // The clip starts assembled; it only moves when Play is pressed.
    const clip = gltf.animations.find(animation => animation.name === 'assemble')
      || gltf.animations[0];
    if (clip) {
      this._clipDuration = clip.duration;
      this._mixer = new THREE.AnimationMixer(gltf.scene);
      this._action = this._mixer.clipAction(clip);
      this._action.setLoop(THREE.LoopOnce, 1);
      this._action.clampWhenFinished = true;
      this._action.play();
      this._action.paused = true;
      this._mixer.update(0);
      this._mixer.addEventListener('finished', event => {
        if (event.action !== this._action) return;
        this._playing = false;
        this._updatePlayButton();
        this._buildMarkers();
        this._updateInfo();
        this._wake();
      });
    } else {
      this._playBtn.disabled = true;
      this._playBtn.title = 'This model has no construction clip';
    }
    this._updatePlayButton();

    this._connections = meta.connections.filter(conn =>
      conn.members.every(id => byId.has(id)));
    if (this._connections.length !== meta.connections.length) {
      console.warn('house viewer: dropped connections with missing members');
    }
    this._connById = new Map(this._connections.map(conn => [conn.id, conn]));
    this._linkConnections();

    this._applyMaterials();
    this._frameScene(gltf.scene);
    this._resize();
    this._buildMarkers();
  }

  _linkConnections() {
    const inverse = new THREE.Matrix4();
    for (const conn of this._connections) {
      const anchor = this._meshById.get(conn.anchor)
        || this._meshById.get(conn.members[0]);
      if (!anchor) continue;
      anchor.updateWorldMatrix(true, false);
      inverse.copy(anchor.matrixWorld).invert();
      conn._anchorMesh = anchor;
      conn._local = new THREE.Vector3()
        .fromArray(conn.point).applyMatrix4(inverse);
    }
  }

  _frameScene(root) {
    this._sceneBox = new THREE.Box3().setFromObject(root);
    this._sceneSize = this._sceneBox.getSize(new THREE.Vector3());
    this._applyHome();
  }

  _applyHome() {
    if (!this._sceneSize || this._userMoved) return;
    const target = new THREE.Vector3(0, 3.55, 0);
    const fov = THREE.MathUtils.degToRad(this._camera.fov);
    const fitHeight = (this._sceneSize.y / 2) / Math.tan(fov / 2);
    const fitWidth = (this._sceneSize.x / 2) / Math.tan(fov / 2)
      / Math.max(0.35, this._camera.aspect);
    const distance = Math.max(fitHeight, fitWidth) * 1.22;
    const theta = THREE.MathUtils.degToRad(35);
    const phi = THREE.MathUtils.degToRad(68);
    this._camera.position.set(
      target.x + distance * Math.sin(phi) * Math.sin(theta),
      target.y + distance * Math.cos(phi),
      target.z + distance * Math.sin(phi) * Math.cos(theta),
    );
    this._controls.target.copy(target);
    this._controls.minDistance = distance * 0.42;
    this._controls.maxDistance = distance * 3.2;
    this._controls.update();
  }

  // -- playback -----------------------------------------------------------
  _updatePlayButton() {
    this._playBtn.textContent = this._playing ? 'Pause' : 'Play';
    this._playBtn.setAttribute('aria-label',
      this._playing ? 'Pause the construction clip' : 'Play the construction clip');
    this._playBtn.setAttribute('aria-pressed', String(this._playing));
  }

  // -- peel ---------------------------------------------------------------
  _setPeel(stop) {
    this._peel = stop;
    this._peelBtns.forEach(button => {
      button.setAttribute('aria-pressed',
        String(button.dataset.peel === stop));
    });
    this._applyMaterials();
    this._updateInfo();
    this._wake();
  }

  _peelGhosts(piece) {
    if (!piece) return false;
    if (this._peel === 'solid') return false;
    if (this._peel === 'roof') return piece.group === 'roof';
    if (this._peel === 'upper') {
      const f1 = this._levels.F1 ?? 3.27;
      return piece.group === 'roof' || piece.center[1] >= f1 - 0.01;
    }
    // "Frame" keeps every timber and hides the masonry: foundation, pads,
    // stones and the ground plane.
    if (this._peel === 'frame') return piece.group === 'base';
    return false;
  }

  // -- picking ------------------------------------------------------------
  _pickMarker(clientX, clientY) {
    if (!this._markers.length) return null;
    const rect = this._canvas.getBoundingClientRect();
    let best = null;
    let bestDistance = 26 * 26;
    const point = new THREE.Vector3();
    for (const { conn, sprite } of this._markers) {
      if (!sprite.visible) continue;
      point.copy(sprite.position).project(this._camera);
      if (point.z < -1 || point.z > 1) continue;
      const x = rect.left + (point.x * 0.5 + 0.5) * rect.width;
      const y = rect.top + (-point.y * 0.5 + 0.5) * rect.height;
      const distance = (x - clientX) ** 2 + (y - clientY) ** 2;
      if (distance < bestDistance) {
        bestDistance = distance;
        best = conn;
      }
    }
    return best;
  }

  _pickPiece(clientX, clientY) {
    const rect = this._canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    const ndc = new THREE.Vector2(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1,
    );
    this._raycaster.setFromCamera(ndc, this._camera);
    const solid = [];
    const all = [];
    for (const mesh of this._meshes) {
      if (!mesh.visible) continue;
      all.push(mesh);
      if (mesh.material !== this._ghostMaterial) solid.push(mesh);
    }
    let hits = this._raycaster.intersectObjects(solid, false);
    if (!hits.length) hits = this._raycaster.intersectObjects(all, false);
    return hits.length ? hits[0].object : null;
  }

  _hoverAt(clientX, clientY) {
    if (!this._loaded) return;
    // A pointer that has come back from an overlay cancels the pending clear
    // that its pointerleave scheduled.
    clearTimeout(this._clearTimer);
    const marker = this._pickMarker(clientX, clientY);
    if (marker) {
      if (this._hoveredConnection !== marker) {
        this._hoveredConnection = marker;
        this._hoveredPiece = this._markerPiece || marker.anchor
          || marker.members[0];
        if (!this._markerPiece) this._markerPiece = this._hoveredPiece;
        this._refresh();
      }
      this._canvas.style.cursor = 'pointer';
      return;
    }

    // A pinned connection stays the subject until it is cleared or another
    // marker/piece is clicked; moving over unrelated timbers should not undo
    // the focus the reader asked for.
    if (this._focusedConnection) {
      if (this._hoveredConnection) {
        this._hoveredConnection = null;
        this._refresh();
      }
      this._canvas.style.cursor = 'default';
      return;
    }

    const mesh = this._pickPiece(clientX, clientY);
    const piece = mesh ? mesh.userData.pieceId : null;
    if (piece !== this._hoveredPiece || this._hoveredConnection) {
      this._hoveredConnection = null;
      this._hoveredPiece = piece;
      if (piece) this._markerPiece = piece;
      this._refresh();
    }
    this._canvas.style.cursor = piece ? 'pointer' : 'grab';
  }

  _clearHoverSoon() {
    clearTimeout(this._clearTimer);
    this._clearTimer = setTimeout(() => this._clearHover(), 140);
  }

  _clearHover() {
    clearTimeout(this._clearTimer);
    this._hoveredPiece = null;
    this._hoveredConnection = null;
    if (!this._pinnedPiece && !this._focusedConnection) this._markerPiece = null;
    this._refresh();
  }

  _clickAt(clientX, clientY) {
    if (!this._loaded) return;
    const marker = this._pickMarker(clientX, clientY);
    if (marker) {
      if (this._focusedConnection === marker) this._clearFocus();
      else this._focus(marker);
      return;
    }
    const mesh = this._pickPiece(clientX, clientY);
    if (!mesh) {
      this._clearFocus();
      return;
    }
    const piece = mesh.userData.pieceId;
    this._focusedConnection = null;
    this._hoveredConnection = null;
    this._pinnedPiece = this._pinnedPiece === piece ? null : piece;
    this._hoveredPiece = this._pinnedPiece;
    this._markerPiece = this._pinnedPiece;
    this.pause();
    this._refresh();
  }

  _focus(conn, { anchor = true } = {}) {
    this._focusedConnection = conn;
    this._hoveredConnection = conn;
    this._pinnedPiece = null;
    this._markerPiece = conn.anchor || conn.members[0];
    this.pause();
    this._refresh();
    this._canvas.style.cursor = 'pointer';
    if (anchor) this._writeAnchor(conn);
  }

  _clearFocus({ rehover = true } = {}) {
    this._focusedConnection = null;
    this._hoveredConnection = null;
    this._pinnedPiece = null;
    this._markerPiece = null;
    this._hoveredPiece = null;
    this._refresh();
    if (isViewHash(location.hash)) history.replaceState(null, '', '#house');
    if (rehover && this._lastPointer) {
      this._hoverAt(this._lastPointer.x, this._lastPointer.y);
    }
  }

  // -- shareable view anchors ---------------------------------------------
  // Focus pushes a hash entry, so the catalog link that follows pushes another
  // one and Back lands here again.  Camera/target keep the orbit, peel keeps the
  // layer visibility and time keeps the pose when the clip was paused.
  _writeAnchor(conn) {
    if (!this._controls) return;
    const p = this._camera.position;
    const t = this._controls.target;
    const parts = [
      'p=' + [p.x, p.y, p.z].map(round2).join(','),
      't=' + [t.x, t.y, t.z].map(round2).join(','),
    ];
    if (this._peel !== 'solid') parts.push('peel=' + encodeURIComponent(this._peel));
    if (this.currentTime > 0.01) parts.push('time=' + round2(this.currentTime));
    const hash = '#house/' + encodeURIComponent(conn.id) + '?' + parts.join('&');
    if (location.hash !== hash) location.hash = hash;
  }

  // Restore a "#house/<id>?…" anchor, including when the lazy viewer has not
  // loaded its model yet.  Returns false for hashes that are not ours.
  restoreFromHash(hash) {
    const match = VIEW_HASH.exec(hash || '');
    if (!match) return false;
    if (!this._loaded) {
      this._pendingHash = hash;
      return true;
    }
    const conn = this._connById.get(decodeURIComponent(match[1]));
    if (!conn) return false;
    const params = new URLSearchParams(match[2] || '');
    const peel = params.get('peel');
    if (peel && this._peelBtns.some(button => button.dataset.peel === peel)) {
      this._setPeel(peel);
    }
    const time = Number(params.get('time'));
    if (params.has('time') && Number.isFinite(time)) this.currentTime = time;
    this._focus(conn, { anchor: false });
    const position = triple(params.get('p'));
    const target = triple(params.get('t'));
    if (position && target) {
      this._camera.position.set(...position);
      this._controls.target.set(...target);
      this._controls.update();
      this._userMoved = true;   // do not let a later resize reset to home
      this._wake();
    }
    return true;
  }

  // -- materials, outlines and markers -----------------------------------
  _refresh() {
    this._applyMaterials();
    this._buildMarkers();
    this._updateInfo();
    this._wake();
  }

  _applyMaterials() {
    if (!this._meshes) return;
    const active = this._hoveredConnection || this._focusedConnection;
    const members = active ? new Set(active.members) : null;
    const activePiece = active ? null : (this._hoveredPiece || this._pinnedPiece);
    this._ghostMaterial.opacity = active ? 0.075 : 0.13;
    const outlines = new Set();
    for (const mesh of this._meshes) {
      const id = mesh.userData.pieceId;
      const piece = this._pieces[id];
      let ghost;
      let focus = false;
      if (active) {
        focus = members.has(id);
        ghost = !focus;
      } else {
        ghost = this._peelGhosts(piece);
        focus = activePiece === id;
      }
      mesh.material = ghost ? this._ghostMaterial
        : (focus ? this._focusMaterial : this._solidMaterial);
      if (focus) outlines.add(mesh);
    }
    for (const [mesh, line] of this._outlines) {
      line.visible = outlines.has(mesh);
    }
    for (const mesh of outlines) this._outlineFor(mesh).visible = true;
  }

  _outlineFor(mesh) {
    let line = this._outlines.get(mesh);
    if (!line) {
      const edges = new THREE.EdgesGeometry(mesh.geometry, 28);
      line = new THREE.LineSegments(edges, this._outlineMaterial);
      line.renderOrder = 8;
      line.raycast = () => {};
      mesh.add(line);
      this._outlines.set(mesh, line);
    }
    return line;
  }

  _buildMarkers() {
    if (!this._loaded) return;
    const active = this._hoveredConnection || this._focusedConnection;
    let pieceId = this._hoveredPiece || this._pinnedPiece;
    if (active) {
      pieceId = this._hoveredConnection
        ? (this._hoveredPiece || active.anchor || active.members[0])
        : (active.anchor || active.members[0]);
    }
    if (this._playing) pieceId = null;

    let list = [];
    if (pieceId && this._pieces[pieceId]) {
      list = this._pieces[pieceId].connections
        .map(id => this._connById.get(id))
        .filter(Boolean);
    }
    if (active && !list.includes(active)) list.push(active);
    if (active) list = [active, ...list.filter(conn => conn !== active)];

    while (this._markerSprites.length < list.length) {
      const sprite = new THREE.Sprite(this._markerMaterial);
      sprite.renderOrder = 20;
      sprite.raycast = () => {};
      this._scene.add(sprite);
      this._markerSprites.push(sprite);
    }
    this._markerSprites.forEach((sprite, i) => {
      const conn = list[i];
      sprite.visible = !!conn;
      sprite.userData.connection = conn || null;
      if (!conn) return;
      const isActive = conn === active;
      sprite.material = isActive
        ? this._markerActiveMaterial : this._markerMaterial;
      sprite.scale.setScalar(isActive ? 0.31 : 0.24);
    });
    this._markers = list.map((conn, i) => ({
      conn, sprite: this._markerSprites[i],
    }));
    if (this._markers.length) this._pulseUntil = performance.now() + 3500;
    this._updateMarkerPositions();
    if (this._markers.length) this._wake();
  }

  _updateMarkerPositions() {
    if (!this._markers.length) return;
    const point = this._tmp;
    for (const { conn, sprite } of this._markers) {
      const anchor = conn._anchorMesh;
      if (!anchor || !conn._local) {
        sprite.visible = false;
        continue;
      }
      anchor.updateWorldMatrix(true, false);
      point.copy(conn._local).applyMatrix4(anchor.matrixWorld);
      sprite.position.copy(point);
    }
  }

  _pulseMarkers() {
    const now = performance.now();
    const animate = !REDUCED && now < this._pulseUntil;
    const t = now * 0.001;
    for (const { conn, sprite } of this._markers) {
      const active = conn === this._hoveredConnection
        || conn === this._focusedConnection;
      const base = active ? 0.31 : 0.24;
      sprite.scale.setScalar(animate
        ? base * (1 + Math.sin(t * 3.3) * 0.07) : base);
    }
    return animate;
  }

  _makeMarkerTexture() {
    const size = 96;
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const context = canvas.getContext('2d');
    const centre = size / 2;
    const glow = context.createRadialGradient(
      centre, centre, 3, centre, centre, centre);
    glow.addColorStop(0, 'rgba(255, 245, 228, 0.98)');
    glow.addColorStop(0.32, 'rgba(255, 190, 138, 0.92)');
    glow.addColorStop(0.62, 'rgba(224, 118, 90, 0.30)');
    glow.addColorStop(1, 'rgba(224, 118, 90, 0)');
    context.fillStyle = glow;
    context.fillRect(0, 0, size, size);
    context.beginPath();
    context.arc(centre, centre, size * 0.24, 0, Math.PI * 2);
    context.strokeStyle = 'rgba(255, 246, 232, 0.95)';
    context.lineWidth = size * 0.055;
    context.stroke();
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  // -- information panel --------------------------------------------------
  _updateInfo() {
    if (!this._loaded) return;
    const active = this._hoveredConnection || this._focusedConnection;
    const pieceId = active ? null : (this._hoveredPiece || this._pinnedPiece);
    const pinned = !!this._focusedConnection || !!this._pinnedPiece;
    const key = (active ? 'c:' + active.id : (pieceId ? 'p:' + pieceId : ''))
      + (pinned ? '!' : '');
    if (key === this._lastInfoKey) return;
    this._lastInfoKey = key;

    if (active) {
      this._info.hidden = false;
      this._info.innerHTML = this._connectionCard(active, pinned);
      this._markBrowserCurrent(active);
      const names = this._memberNames(active).join(', ');
      this._announce(`${this._meta.kinds[active.kind].title}: ${names}`);
      return;
    }
    if (pieceId && this._pieces[pieceId]) {
      this._info.hidden = false;
      this._info.innerHTML = this._pieceCard(pieceId, pinned);
      this._markBrowserCurrent(null);
      this._announce(`${this._pieces[pieceId].name}, `
        + `${this._pieces[pieceId].connections.length} connections`);
      return;
    }
    this._info.hidden = true;
    this._info.innerHTML = '';
    this._markBrowserCurrent(null);
    this._announce('');
  }

  _memberNames(conn) {
    const names = conn.members.map(id => this._pieces[id]?.name || id);
    return [...new Set(names)];
  }

  _connectionCard(conn, pinned) {
    const kind = this._meta.kinds[conn.kind];
    const members = this._memberNames(conn).join(' ↔ ');
    const catalog = kind.catalog;
    let link;
    if (catalog) {
      link = `<a href="#${escapeHtml(catalog.slug)}">`
        + `${kind.match === 'exact' ? 'Catalog joint' : 'Related catalog joint'}: `
        + `${escapeHtml(catalog.title)}`
        + (catalog.jp ? ` <span class="jp" lang="ja">${escapeHtml(catalog.jp)}</span>` : '')
        + ' →</a>';
    } else {
      link = this._scheduleLink();
    }
    const badge = pinned
      ? '<span class="badge pinned">Pinned</span>'
      : (kind.match === 'related' ? '<span class="badge">Related</span>' : '');
    return `<h3>${escapeHtml(kind.title)}${badge}</h3>
      <span class="sub">${escapeHtml(members)}</span>
      <p class="desc">${escapeHtml(kind.description)}</p>
      <div class="links">${link}</div>
      ${pinned ? '<button type="button" class="clear" data-clear>Clear focus</button>' : ''}`;
  }

  _pieceCard(pieceId, pinned) {
    const piece = this._pieces[pieceId];
    const group = this._house.groups[piece.group] || piece.group;
    const connections = piece.connections
      .map(id => this._connById.get(id)).filter(Boolean);
    // One representative instance per family, so a chip opens that joint.
    const families = new Map();
    for (const conn of connections) {
      if (!families.has(conn.kind)) families.set(conn.kind, conn);
    }
    const list = families.size
      ? `<ul class="titles">${[...families].slice(0, 8)
        .map(([kind, conn]) => `<li><button type="button" data-connection="${conn.id}">`
          + `${escapeHtml(this._meta.kinds[kind].title)}</button></li>`).join('')}</ul>`
      : '<p class="desc">A foundation or ground piece; it does not move in the clip.</p>';
    const note = this._playing
      ? '<p class="desc">Playing the construction clip: pause to inspect the joints.</p>'
      : (connections.length
        ? '<p class="desc">Move over a joint marker to name the connection.</p>' : '');
    return `<h3>${escapeHtml(piece.name)}${pinned ? '<span class="badge pinned">Selected</span>' : ''}</h3>
      <span class="sub">${escapeHtml(group)} · ${connections.length} connection${connections.length === 1 ? '' : 's'}</span>
      ${note}${list}
      <div class="links">${this._scheduleLink()}</div>
      ${pinned ? '<button type="button" class="clear" data-clear>Clear selection</button>' : ''}`;
  }

  _scheduleLink() {
    const repo = (this.dataset.repoUrl || '').replace(/\/$/, '');
    if (repo) {
      return `<a href="${escapeHtml(repo)}/blob/main/house/README.md#joint-schedule" target="_blank" rel="noopener">House joint schedule →</a>`;
    }
    return '<a href="#house">House notes and joint schedule →</a>';
  }

  _announce(text) {
    if (this._live.textContent !== text) this._live.textContent = text;
  }

  // -- connection index ---------------------------------------------------
  _toggleBrowser(open) {
    const hadFocus = this._browser.contains(this.shadowRoot.activeElement);
    this._browser.hidden = !open;
    this._browseBtn.setAttribute('aria-expanded', String(open));
    if (!open) {
      if (hadFocus) this._browseBtn.focus();
      return;
    }
    this._buildBrowser();
    this._browserSearch.focus();
  }

  _buildBrowser() {
    if (this._browserBuilt) return;
    this._browserBuilt = true;
    const groups = new Map();
    for (const conn of this._connections) {
      if (!groups.has(conn.kind)) groups.set(conn.kind, []);
      groups.get(conn.kind).push(conn);
    }
    const fragment = document.createDocumentFragment();
    for (const [kind, list] of groups) {
      const meta = this._meta.kinds[kind];
      list.sort((a, b) => a.point[1] - b.point[1]
        || a.point[0] - b.point[0] || a.point[2] - b.point[2]);
      const section = document.createElement('section');
      const heading = document.createElement('h4');
      heading.innerHTML = `${escapeHtml(meta.title)} <span>${list.length}</span>`;
      section.append(heading);
      const ul = document.createElement('ul');
      for (const conn of list) {
        const li = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.connection = conn.id;
        const names = this._memberNames(conn).join(' ↔ ');
        const point = conn.point.map(value =>
          value.toFixed(2).replace(/\.?0+$/, '')).join(', ');
        button.textContent = `${names} · ${point}`;
        button.dataset.search = `${meta.title} ${names} ${point}`.toLowerCase();
        li.append(button);
        ul.append(li);
      }
      section.append(ul);
      fragment.append(section);
    }
    this._browserList.replaceChildren(fragment);
  }

  _filterBrowser() {
    const query = this._browserSearch.value.trim().toLowerCase();
    this._browserList.scrollTop = 0;
    let shown = 0;
    for (const section of this._browserList.querySelectorAll('section')) {
      let inSection = 0;
      for (const li of section.querySelectorAll('li')) {
        const hay = li.querySelector('button')?.dataset.search
          || li.textContent.toLowerCase();
        const match = !query || hay.includes(query);
        li.hidden = !match;
        if (match) inSection += 1;
      }
      section.hidden = !inSection;
      shown += inSection;
    }
    let empty = this._browserList.querySelector('.empty');
    if (!shown) {
      if (!empty) {
        empty = document.createElement('p');
        empty.className = 'empty';
        empty.textContent = 'No connection matches that filter.';
        this._browserList.append(empty);
      }
      empty.hidden = false;
    } else if (empty) {
      empty.hidden = true;
    }
  }

  _markBrowserCurrent(conn) {
    if (!this._browserBuilt) return;
    this._browserList.querySelectorAll('button[data-connection]').forEach(button => {
      if (conn && button.dataset.connection === conn.id) {
        button.setAttribute('aria-current', 'true');
      } else {
        button.removeAttribute('aria-current');
      }
    });
  }

  // -- rendering ----------------------------------------------------------
  _resize() {
    if (!this._renderer) return;
    const rect = this.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    this._renderer.setSize(rect.width, rect.height, false);
    this._camera.aspect = rect.width / rect.height;
    this._camera.updateProjectionMatrix();
    this._applyHome();
  }

  _canRender() {
    return !!(this._ok && !document.hidden && this._visible);
  }

  _wake() {
    if (!this._canRender() || this._raf) return;
    this._clock.getDelta();
    this._raf = requestAnimationFrame(this._tick);
  }

  _stopLoop() {
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = 0;
  }

  _tick = () => {
    this._raf = 0;
    if (!this._canRender() || !this._renderer) return;
    const delta = Math.min(this._clock.getDelta(), 0.05);
    let active = false;
    if (this._playing && this._mixer) {
      this._mixer.update(delta);
      active = true;
    }
    if (this._controls) {
      if (this._controls.update()) active = true;
    }
    if (this._markers.length && this._pulseMarkers()) active = true;
    this._updateMarkerPositions();
    this._renderer.render(this._scene, this._camera);
    if (active && !this._raf) {
      this._raf = requestAnimationFrame(this._tick);
    }
  };

  // -- fallback -----------------------------------------------------------
  _showError(message) {
    this._ok = false;
    this._stage = this.closest('.stage');
    this._stage?.classList.add('error');
    this._stage?.classList.remove('ready');
    this._error.hidden = false;
    const poster = this.dataset.poster
      ? `<img src="${escapeHtml(this.dataset.poster)}" alt="The house frame at rest">`
      : '';
    const repo = (this.dataset.repoUrl || '').replace(/\/$/, '');
    const source = this.dataset.src
      ? `<a href="${escapeHtml(this.dataset.src)}" download>Download the house GLB</a>`
      : 'House model';
    const notes = repo
      ? ` · <a href="${escapeHtml(repo)}/blob/main/house/README.md">House notes</a>`
      : '';
    this._error.innerHTML = `${poster}
      <h3>The interactive house could not start</h3>
      <p>${escapeHtml(message)}</p>
      <p>${source}${notes}</p>`;
    this._loadingEl?.setAttribute('hidden', '');
    this.shadowRoot.querySelector('.bar')?.setAttribute('hidden', '');
    this._info.hidden = true;
    this._browser.hidden = true;
    this.dispatchEvent(new Event('error'));
  }
}

if (!customElements.get('house-viewer')) {
  customElements.define('house-viewer', HouseViewer);
}
