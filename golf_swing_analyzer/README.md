# 🏌️ Golf Swing 3D Analyzer

Record your golf swing with a camera, turn it into a **3D stick-figure skeleton**,
and play it back **frame by frame** — spinning the view around to see your swing
from any angle (face-on, down-the-line, top-down, or anywhere in between).

No special sensors or suits. Just a camera and this software.

---

## How it works (the 10-year-old version)

1. **A camera watches you swing.** (`capture.py`)
2. **A "pose AI" plays connect-the-dots on your body** in every picture the
   camera takes — finding your shoulders, elbows, wrists, hips, knees, and
   ankles. It gives us those dots in real 3D (in meters). We use Google's free
   **MediaPipe** for this.
3. **We save all those dots** into a file called `swing.json` — basically a
   flip-book of your body, one page per frame.
4. **A 3D viewer draws the skeleton** from the dots and lets you play it like a
   flip-book: play, pause, step one frame at a time, slow it down, and drag with
   your mouse to look at the swing from any side. (`viewer/`)

```
 camera ──► capture.py ──► swing.json ──► viewer (your web browser)
 (eyes)     (pose AI)      (flip-book)    (3D playback)
```

---

## Quick start (laptop + webcam — the easiest build)

```bash
cd golf_swing_analyzer
pip install -r requirements.txt        # one time only

# 1) Record a swing (press 'q' to stop, or use --duration)
python capture.py --duration 6 --save-video

# 2) Open the 3D viewer in your browser
python server.py
```

`server.py` opens a page at `http://localhost:8000/viewer/`. Pick your swing
from the dropdown (or drag a `swing.json` onto the page) and press **play**.

> **First time?** The viewer already shows a built-in *demo* swing so you can
> try the controls before recording anything real.

---

## Using the viewer

| Control | What it does |
|---|---|
| ▶ / ⏸ (or **Spacebar**) | Play / pause |
| ⏮ ⏭ (or **← / →** keys) | Step one frame back / forward |
| Slider | Scrub to any moment in the swing |
| Speed | Slow-mo (0.1×) up to 2× |
| **Drag mouse** | Orbit the camera around the skeleton |
| Scroll | Zoom in / out |
| Face-on / Down-the-line / Top | Jump to classic golf camera angles |
| Hand path | Show/hide the arc your hands travel (a stand-in for the club path / swing plane) |

**Colors:** your left side is **blue**, right side is **orange**, spine/center is **green**.

**On-screen numbers** (rough estimates from the skeleton, measured against your
starting "address" pose):
- **Shoulder turn** – how far your shoulders have rotated
- **Hip turn** – how far your hips have rotated
- **Spine tilt** – how far your spine leans from straight-up

---

## Command reference

`capture.py`
```
--source 0            camera number (0,1,...) OR a video file like swing.mp4
--duration 6          auto-stop after N seconds (0 = press 'q' to stop)
--output swings       folder to save into
--name my_driver      name this swing
--complexity 0|1|2    pose model: 0 fast (Raspberry Pi), 1 balanced, 2 accurate
--save-video          also keep the raw camera video
--no-window           no preview window (for headless devices)
--width/--height/--fps  request a camera resolution / frame rate
```

`server.py`
```
--port 8000
--host 0.0.0.0        reach the viewer from your phone on the same Wi-Fi
--no-open             don't auto-open a browser
```

---

## Tips for a good capture

- **Stand back** so your whole body *and* the club fit in the frame with room to
  spare. Cutting off the club or your hands ruins the tracking.
- **Light yourself well.** The AI struggles in the dark. Face a window or a lamp.
- **Fast shutter / high FPS beats megapixels.** A golf club head moves ~100 mph,
  so a slow camera turns it into a blur the AI can't read. 60 fps (or faster) and
  good light matter far more than resolution. This is why phone "slow-mo" modes
  make great swing videos — record one and feed it in with `--source myswing.mp4`.
- **One person in frame.** MediaPipe tracks a single body at a time.
- Record from **down-the-line** (behind, looking toward the target) *or*
  **face-on** — both work, and you can rotate freely in 3D afterward.

## Limitations (be honest with yourself)

This uses a single ordinary camera, so the depth (how far toward/away from the
camera each joint is) is an **educated guess**, not a laser-measured truth.
It's excellent for seeing *movement, sequence, and timing* — the shape of your
swing — but it is not a $20,000 marker-based motion-capture lab. Treat the angle
numbers as consistent relative feedback, not certified measurements.

## Files

```
golf_swing_analyzer/
├── capture.py          # camera + pose AI -> swing.json
├── server.py           # serves the viewer to your browser
├── generate_sample.py  # makes the built-in demo swing
├── requirements.txt
├── HARDWARE.md         # how to build the physical device (parts + wiring)
├── viewer/
│   ├── index.html      # the 3D playback page
│   ├── viewer.js       # 3D drawing + playback logic
│   ├── style.css
│   └── sample_swing.json   # built-in demo
└── swings/             # your recordings land here (one folder per swing)
```

See **[HARDWARE.md](HARDWARE.md)** to build it as a standalone device
(Raspberry Pi) or the simple tripod-and-webcam rig.
