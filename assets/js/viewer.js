// The joint viewer: one three.js scene for the whole visit.
//
// The canvas lives in the root layout, outside the element dp-swap replaces,
// so following a link keeps the renderer and only swaps the model. The page
// says which model it wants with `data-glb` on the swapped-in article; this
// script reads it on the first load and again after every swap.
//
// The sidebar is outside the swap too, so this script also moves
// `aria-current` and owns the filter and the arrow-key navigation.

import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const viewer = document.getElementById("viewer");
const canvas = document.getElementById("viewer-canvas");
const nav = document.getElementById("joint-nav");
const filter = document.getElementById("joint-filter");
const empty = document.getElementById("joint-empty");

// ------------------------------------------------------------------ scene

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.NeutralToneMapping;

const scene = new THREE.Scene();
scene.background = new THREE.Color("#f6f8fa");
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.7;

const sun = new THREE.DirectionalLight(0xffffff, 1.1);
sun.position.set(3, 5, 4);
scene.add(sun);

const camera = new THREE.PerspectiveCamera(40, 1, 0.001, 100);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.autoRotateSpeed = 1.5;

const loader = new GLTFLoader();
const clock = new THREE.Clock();
let model = null;
let mixer = null;
let home = null; // the camera position `Reset view` returns to
let wanted = null; // the URL most recently asked for; a slower load that finishes later is dropped

function resize() {
  const { clientWidth: w, clientHeight: h } = canvas;
  if (canvas.width !== w * renderer.getPixelRatio() || canvas.height !== h * renderer.getPixelRatio()) {
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(h, 1);
    camera.updateProjectionMatrix();
  }
}

renderer.setAnimationLoop(() => {
  resize();
  const dt = clock.getDelta();
  if (mixer && playing) mixer.update(dt);
  controls.update();
  renderer.render(scene, camera);
});

function dispose(root) {
  root.traverse((node) => {
    node.geometry?.dispose();
    for (const material of [node.material].flat().filter(Boolean)) {
      for (const value of Object.values(material)) value?.isTexture && value.dispose();
      material.dispose();
    }
  });
}

// Frames the model from a three-quarter view. The bounding sphere and not the
// box, so the distance does not jump while the timbers slide apart.
function frame(root) {
  const sphere = new THREE.Box3().setFromObject(root).getBoundingSphere(new THREE.Sphere());
  const distance = (sphere.radius * 1.05) / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2));
  const direction = new THREE.Vector3(1, 0.8, 1.2).normalize();
  controls.target.copy(sphere.center);
  camera.position.copy(sphere.center).addScaledVector(direction, distance);
  camera.near = distance / 100;
  camera.far = distance * 100;
  camera.updateProjectionMatrix();
  home = { position: camera.position.clone(), target: controls.target.clone() };
}

async function show(url) {
  if (url === wanted) return;
  wanted = url;
  if (!url) {
    clear();
    viewer.dataset.state = "empty";
    return;
  }
  viewer.dataset.state = "loading";
  try {
    const gltf = await loader.loadAsync(url);
    if (url !== wanted) return dispose(gltf.scene);
    clear();
    model = gltf.scene;
    scene.add(model);
    // Measured closed: the animation's first frame is the assembled joint.
    mixer = new THREE.AnimationMixer(model);
    for (const clip of gltf.animations) mixer.clipAction(clip).play();
    mixer.setTime(0);
    frame(model);
    viewer.dataset.state = "ready";
  } catch (error) {
    if (url !== wanted) return;
    console.error(error);
    viewer.dataset.state = "error";
  }
}

function clear() {
  if (!model) return;
  scene.remove(model);
  dispose(model);
  model = mixer = null;
}

// ---------------------------------------------------------------- toolbar

let playing = true;
const play = document.getElementById("viewer-play");
const rotate = document.getElementById("viewer-rotate");

play.addEventListener("click", () => {
  playing = !playing;
  play.setAttribute("aria-pressed", playing);
});
rotate.addEventListener("click", () => {
  controls.autoRotate = !controls.autoRotate;
  rotate.setAttribute("aria-pressed", controls.autoRotate);
});
document.getElementById("viewer-reset").addEventListener("click", () => {
  if (!home) return;
  camera.position.copy(home.position);
  controls.target.copy(home.target);
});

// ---------------------------------------------------------------- sidebar

const links = () => [...nav.querySelectorAll(".nav-link")];

function mark(pathname) {
  for (const link of links()) {
    if (new URL(link.href).pathname === pathname) {
      link.setAttribute("aria-current", "page");
      link.scrollIntoView({ block: "nearest" });
    } else {
      link.removeAttribute("aria-current");
    }
  }
}

filter.addEventListener("input", () => {
  // Digits match the number whatever its padding: "7" finds Joint 007.
  const query = filter.value.trim().toLowerCase().replace(/^0+(?=\d)/, "");
  let shown = 0;
  for (const link of links()) {
    const text = link.textContent.toLowerCase().replace(/\b0+(?=\d)/g, "");
    const match = !query || text.includes(query);
    link.parentElement.hidden = !match;
    shown += match;
  }
  empty.hidden = shown > 0;
});

// Up and down walk the visible entries, so they also walk a filtered list.
document.addEventListener("keydown", (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  const typing = event.target.matches("input, textarea");
  if (event.key === "/" && !typing) {
    event.preventDefault();
    filter.focus();
    return;
  }
  if (event.key === "Escape" && event.target === filter) {
    filter.value = "";
    filter.dispatchEvent(new Event("input"));
    filter.blur();
    return;
  }
  if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
  if (typing && event.target !== filter) return;
  const visible = links().filter((link) => !link.parentElement.hidden);
  const at = visible.findIndex((link) => link.hasAttribute("aria-current"));
  const step = event.key === "ArrowDown" ? 1 : -1;
  const target = visible[Math.min(Math.max(at + step, 0), visible.length - 1)];
  if (!target || target === visible[at]) return;
  event.preventDefault();
  target.click();
});

// ------------------------------------------------------------------- page

function sync() {
  const article = document.querySelector("#outlet [data-glb], #outlet article");
  show(article?.dataset.glb ?? null);
  mark(location.pathname);
}

document.addEventListener("dp:afterSettle", sync);
window.addEventListener("popstate", () => queueMicrotask(sync));
sync();
