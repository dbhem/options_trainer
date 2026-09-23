// viewer.js -- draws the 3D skeleton and lets you play the swing frame by frame.
//
// Big picture:
//   - We build a "scene": a floor, some lights, and a stick figure.
//   - The stick figure is a bunch of little balls (joints) joined by lines (bones).
//   - Every frame of the swing is a list of 33 points in 3D.
//   - To "play", we just move the balls to the next frame's points, over and over.
//   - OrbitControls lets you drag with the mouse to spin the camera around.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ---------------------------------------------------------------------------
// Left/right coloring so you can tell the sides apart (like left vs right shoe).
const LEFT = new Set([1,2,3,7,9,11,13,15,17,19,21,23,25,27,29,31]);
const RIGHT = new Set([4,5,6,8,10,12,14,16,18,20,22,24,26,28,30,32]);
const COL_LEFT = 0x4aa3ff;   // blue-ish
const COL_RIGHT = 0xffb020;  // orange-ish
const COL_MID = 0x37c871;    // green (spine / center)

// ---------------------------------------------------------------------------
// Scene setup
const container = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0e1116);
scene.fog = new THREE.Fog(0x0e1116, 6, 16);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.05, 100);
const HOME = new THREE.Vector3(0, 0.9, 3.2);
camera.position.copy(HOME);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0.9, 0);

// Lights
scene.add(new THREE.HemisphereLight(0xbfd4ff, 0x20262e, 0.9));
const key = new THREE.DirectionalLight(0xffffff, 1.1);
key.position.set(3, 6, 4);
scene.add(key);

// Floor grid + solid ground so the figure doesn't float in a void.
const grid = new THREE.GridHelper(10, 20, 0x30475e, 0x1d2833);
scene.add(grid);
const ground = new THREE.Mesh(
  new THREE.CircleGeometry(5, 48),
  new THREE.MeshStandardMaterial({ color: 0x141a22, roughness: 1 })
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.001;
scene.add(ground);

// A little origin marker where the ball would roughly sit (in front of feet).
const ballMarker = new THREE.Mesh(
  new THREE.SphereGeometry(0.021, 16, 16),
  new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x333333 })
);
scene.add(ballMarker);

// ---------------------------------------------------------------------------
// The skeleton (rebuilt whenever we load a swing)
const skeleton = new THREE.Group();
scene.add(skeleton);
let joints = [];      // array of THREE.Mesh (spheres)
let bones = null;     // THREE.LineSegments
let connections = []; // [[a,b], ...]
let trailLeft = null, trailRight = null;

const jointGeo = new THREE.SphereGeometry(0.028, 12, 12);

function clearSkeleton() {
  while (skeleton.children.length) skeleton.remove(skeleton.children[0]);
  joints = [];
  bones = null;
  if (trailLeft) { scene.remove(trailLeft); trailLeft = null; }
  if (trailRight) { scene.remove(trailRight); trailRight = null; }
}

// ---------------------------------------------------------------------------
// Swing data + playback state
let swing = null;      // parsed swing.json
let frames = [];       // convenient reference to swing.frames
let fps = 30;
let cur = 0;           // current frame index (can be fractional while playing)
let playing = false;
let speed = 0.5;
let loop = true;
let lastTime = 0;

// MediaPipe world coords -> Three.js coords.
// MediaPipe: x=right, y=DOWN, z=toward camera, origin ~ between hips (meters).
// Three.js:  y is UP. So we flip y, and flip z so "toward camera" reads sensibly.
// We also shift the whole figure up so the feet rest on the floor (y=0).
let footOffset = 0;
function toVec(l) { return new THREE.Vector3(l[0], -l[1] + footOffset, -l[2]); }

function computeFootOffset(frame) {
  // Lowest body point across the swing's first frame ~ feet; put it on the floor.
  let minY = Infinity;
  for (const l of frame.landmarks) minY = Math.min(minY, -l[1]);
  return -minY;
}

function buildSkeleton() {
  clearSkeleton();
  connections = swing.meta.connections;

  // Joints (skip low-value face points to keep it clean: keep 0 and 11+).
  for (let i = 0; i < 33; i++) {
    const color = LEFT.has(i) ? COL_LEFT : RIGHT.has(i) ? COL_RIGHT : COL_MID;
    const m = new THREE.Mesh(jointGeo, new THREE.MeshStandardMaterial({
      color, emissive: color, emissiveIntensity: 0.25, roughness: 0.5,
    }));
    joints.push(m);
    skeleton.add(m);
  }

  // Bones as one LineSegments object (fast to update).
  const positions = new Float32Array(connections.length * 2 * 3);
  const colors = new Float32Array(connections.length * 2 * 3);
  const c = new THREE.Color();
  connections.forEach((pair, k) => {
    const side = LEFT.has(pair[0]) && LEFT.has(pair[1]) ? COL_LEFT
              : RIGHT.has(pair[0]) && RIGHT.has(pair[1]) ? COL_RIGHT : COL_MID;
    c.setHex(side);
    colors.set([c.r, c.g, c.b, c.r, c.g, c.b], k * 6);
  });
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  bones = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ vertexColors: true }));
  skeleton.add(bones);

  buildTrails();
  updateTrailVisibility();
}

// Draw the path each wrist travels across the WHOLE swing (a stand-in for the
// club arc). Great for seeing swing plane / how "on plane" you are.
function buildTrails() {
  const li = 15, ri = 16; // left_wrist, right_wrist
  const lPts = [], rPts = [];
  for (const f of frames) {
    lPts.push(toVec(f.landmarks[li]));
    rPts.push(toVec(f.landmarks[ri]));
  }
  trailLeft = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(lPts),
    new THREE.LineBasicMaterial({ color: COL_LEFT, transparent: true, opacity: 0.55 })
  );
  trailRight = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(rPts),
    new THREE.LineBasicMaterial({ color: COL_RIGHT, transparent: true, opacity: 0.55 })
  );
  scene.add(trailLeft);
  scene.add(trailRight);
}

// ---------------------------------------------------------------------------
// Put the skeleton into the pose of frame index `i` (rounded).
function setFrame(i) {
  const idx = Math.max(0, Math.min(frames.length - 1, Math.round(i)));
  const lms = frames[idx].landmarks;

  for (let j = 0; j < 33; j++) {
    const v = toVec(lms[j]);
    joints[j].position.copy(v);
    joints[j].visible = lms[j][3] > 0.2; // hide very-low-confidence points
  }

  const pos = bones.geometry.attributes.position;
  connections.forEach((pair, k) => {
    const a = joints[pair[0]].position, b = joints[pair[1]].position;
    pos.array.set([a.x, a.y, a.z, b.x, b.y, b.z], k * 6);
  });
  pos.needsUpdate = true;
  bones.geometry.computeBoundingSphere();

  // Ball marker: roughly under the hands, on the ground.
  const mid = joints[15].position.clone().add(joints[16].position).multiplyScalar(0.5);
  ballMarker.position.set(mid.x, 0.02, mid.z + 0.15);

  updateStats(idx);
}

// ---------------------------------------------------------------------------
// Simple golf metrics (clearly labeled as estimates in the UI).
function groundAngle(a, b) {
  // angle of vector a->b projected on the floor, in degrees.
  return Math.atan2(b.z - a.z, b.x - a.x) * 180 / Math.PI;
}
let addressShoulder = 0, addressHip = 0;
function calibrateAddress() {
  const lms = frames[0].landmarks;
  addressShoulder = groundAngle(toVec(lms[11]), toVec(lms[12]));
  addressHip = groundAngle(toVec(lms[23]), toVec(lms[24]));
}
function wrap(deg) { // keep within -180..180
  while (deg > 180) deg -= 360;
  while (deg < -180) deg += 360;
  return deg;
}
function updateStats(idx) {
  const f = frames[idx];
  document.getElementById('stat-frame').textContent = `${idx + 1} / ${frames.length}`;
  document.getElementById('stat-time').textContent = `${f.t.toFixed(2)} s`;

  const lms = f.landmarks;
  const shoulder = wrap(groundAngle(toVec(lms[11]), toVec(lms[12])) - addressShoulder);
  const hip = wrap(groundAngle(toVec(lms[23]), toVec(lms[24])) - addressHip);
  document.getElementById('stat-shoulder').textContent = `${Math.abs(shoulder).toFixed(0)}°`;
  document.getElementById('stat-hip').textContent = `${Math.abs(hip).toFixed(0)}°`;

  // Spine tilt: angle of hip-mid -> shoulder-mid line away from straight-up.
  const hipMid = toVec(lms[23]).add(toVec(lms[24])).multiplyScalar(0.5);
  const shMid = toVec(lms[11]).add(toVec(lms[12])).multiplyScalar(0.5);
  const spine = shMid.sub(hipMid);
  const tilt = Math.acos(Math.max(-1, Math.min(1, spine.y / spine.length()))) * 180 / Math.PI;
  document.getElementById('stat-spine').textContent = `${tilt.toFixed(0)}°`;
}

// ---------------------------------------------------------------------------
// Playback loop
function animate(now) {
  requestAnimationFrame(animate);
  const dt = (now - lastTime) / 1000 || 0;
  lastTime = now;

  if (playing && frames.length > 1) {
    cur += dt * fps * speed;
    if (cur >= frames.length - 1) {
      if (loop) { cur = 0; }
      else { cur = frames.length - 1; setPlaying(false); }
    }
    scrub.value = Math.round(cur);
    setFrame(cur);
  }
  controls.update();
  renderer.render(scene, camera);
}
requestAnimationFrame(animate);

// ---------------------------------------------------------------------------
// UI wiring
const playBtn = document.getElementById('play');
const scrub = document.getElementById('scrub');

function setPlaying(v) {
  playing = v;
  playBtn.textContent = v ? '⏸' : '▶';
}
playBtn.onclick = () => setPlaying(!playing);
document.getElementById('step-fwd').onclick = () => { setPlaying(false); cur = Math.min(frames.length - 1, Math.round(cur) + 1); scrub.value = cur; setFrame(cur); };
document.getElementById('step-back').onclick = () => { setPlaying(false); cur = Math.max(0, Math.round(cur) - 1); scrub.value = cur; setFrame(cur); };
scrub.oninput = () => { setPlaying(false); cur = +scrub.value; setFrame(cur); };
document.getElementById('speed').onchange = e => { speed = +e.target.value; };
document.getElementById('loop-toggle').onchange = e => { loop = e.target.checked; };
document.getElementById('trail-toggle').onchange = updateTrailVisibility;

function updateTrailVisibility() {
  const on = document.getElementById('trail-toggle').checked;
  if (trailLeft) trailLeft.visible = on;
  if (trailRight) trailRight.visible = on;
}

// Keyboard: space = play/pause, arrows = step frames.
window.addEventListener('keydown', e => {
  if (!frames.length) return;
  if (e.code === 'Space') { e.preventDefault(); setPlaying(!playing); }
  else if (e.code === 'ArrowRight') { document.getElementById('step-fwd').click(); }
  else if (e.code === 'ArrowLeft') { document.getElementById('step-back').click(); }
});

// View presets
document.querySelectorAll('#views button').forEach(btn => {
  btn.onclick = () => setView(btn.dataset.view);
});
function setView(kind) {
  const t = controls.target;
  if (kind === 'faceon') camera.position.set(t.x, t.y, t.z + 3.2);
  else if (kind === 'dtl') camera.position.set(t.x + 3.2, t.y, t.z + 0.001);
  else if (kind === 'top') camera.position.set(t.x, t.y + 3.4, t.z + 0.001);
  else { camera.position.copy(HOME); controls.target.set(0, 0.9, 0); }
}

// Load buttons / dropdown / drag-drop / file input
const dropHint = document.getElementById('drop-hint');
const swingSelect = document.getElementById('swing-select');
const loadError = document.getElementById('load-error');

document.getElementById('load-another').onclick = () => dropHint.classList.remove('hidden');
document.getElementById('refresh-btn').onclick = populateSwingList;
swingSelect.onchange = () => { if (swingSelect.value) loadFromUrl(swingSelect.value); };
document.getElementById('file-input').onchange = e => {
  const file = e.target.files[0];
  if (file) file.text().then(txt => loadSwing(JSON.parse(txt), file.name));
};

['dragover', 'drop'].forEach(ev => window.addEventListener(ev, e => e.preventDefault()));
window.addEventListener('drop', e => {
  const file = e.dataTransfer.files[0];
  if (file) file.text().then(txt => {
    try { loadSwing(JSON.parse(txt), file.name); }
    catch (err) { loadError.textContent = 'That file was not a valid swing.json.'; }
  });
});

async function populateSwingList() {
  try {
    const res = await fetch('/api/swings');
    const list = await res.json();
    swingSelect.innerHTML = '<option value="">— choose a recorded swing —</option>';
    for (const s of list) {
      const o = document.createElement('option');
      o.value = s.url; o.textContent = s.name;
      swingSelect.appendChild(o);
    }
    if (!list.length) {
      swingSelect.innerHTML = '<option value="">(no swings recorded yet — run capture.py)</option>';
    }
  } catch (_) {
    // Not served by server.py (opened as a file). Drag & drop still works.
    swingSelect.innerHTML = '<option value="">(start server.py to list swings)</option>';
  }
}

async function loadFromUrl(url) {
  try {
    const res = await fetch(url);
    loadSwing(await res.json(), url);
  } catch (err) {
    loadError.textContent = 'Could not load that swing.';
  }
}

function loadSwing(data, label) {
  if (!data || !data.frames || !data.frames.length) {
    loadError.textContent = 'This swing has no frames.';
    return;
  }
  swing = data;
  frames = data.frames;
  fps = (data.meta && data.meta.fps) || 30;
  footOffset = 0;
  footOffset = computeFootOffset(frames[0]);

  buildSkeleton();
  calibrateAddress();

  scrub.min = 0;
  scrub.max = frames.length - 1;
  scrub.value = 0;
  cur = 0;
  setFrame(0);
  setPlaying(false);

  document.body.classList.add('loaded');
  dropHint.classList.add('hidden');
  loadError.textContent = '';
}

// ---------------------------------------------------------------------------
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// On start: try to auto-load a bundled sample so the page isn't empty,
// then list any real recorded swings.
populateSwingList();
loadFromUrl('sample_swing.json').catch(() => {});
