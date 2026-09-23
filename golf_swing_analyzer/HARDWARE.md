# 🔧 Building the Golf Swing Analyzer — Hardware Guide

You can build this three ways, from "raid your closet" to "real gadget you mount
on a tripod." All three run the **same software** in this repo.

| Build | Effort | Cost (approx) | Best for |
|---|---|---|---|
| **A. Laptop + webcam** | 5 min | $0–60 | Trying it today |
| **B. Phone as the camera** | 5 min | $0 | Best video quality, no wiring |
| **C. Raspberry Pi device** | 1–2 hrs | $120–180 | A standalone "gadget" at the range/net |
| **D. iPhone Pro LiDAR app** | ~1 hr (build once) | $0 (own the phone) | **Most accurate 3D** — measures depth instead of guessing |

---

## The physics — why the camera choice matters (read this first)

A driver's clubhead reaches **~100 mph (≈45 m/s)**. Your hands and arms move
fast too. Two camera numbers decide whether the pose AI can "see" that motion:

- **Frame rate (fps)** — how many pictures per second. At 30 fps there are big
  gaps between frames during the downswing (the club can travel several feet
  between two pictures). **60 fps or higher** is strongly preferred. This is the
  single most important spec.
- **Shutter speed** — how long each picture is exposed. A long exposure smears a
  fast club into a blur the AI can't find. You want a **fast shutter**
  (≈1/1000 s), which needs **lots of light**.

Everything below is chosen with those two facts in mind. Megapixels barely
matter; **fps + light** are king.

---

## Build A — Laptop + USB webcam (easiest)

**Parts**
- Any laptop (Windows / macOS / Linux) that runs Python.
- A webcam. Built-in works, but an external **1080p60** USB webcam is much
  better because most built-in webcams cap at 30 fps.
- A **tripod** or a stack of books to hold the camera steady at hip/chest height.

**Steps**
1. `pip install -r requirements.txt`
2. Put the camera on the tripod, **~3–4 m (10–13 ft)** from where you'll stand,
   at about **hip-to-chest height**.
3. Frame yourself so your **whole body and the full arc of the club** are inside
   the picture with margin. Do a slow practice swing and confirm nothing gets
   cut off.
4. `python capture.py --duration 6 --save-video`
5. `python server.py` → play it back in 3D.

That's a complete, working analyzer. Builds B and C are refinements.

---

## Build B — Use your phone as the camera (best image quality)

Your phone already has a great sensor and a **slow-motion mode** (120–240 fps).
That is *ideal* for golf. You don't even need a live connection.

1. Set the phone to **Slo-mo** (or 60 fps if no slo-mo) and mount it on a
   phone tripod, framed as in Build A.
2. Record your swing. Transfer the video file to your computer.
3. Analyze the file directly:
   ```bash
   python capture.py --source myswing.mp4 --save-video
   ```
   (`--source` accepts any video file, so no camera drivers or wiring needed.)
4. `python server.py` → 3D playback.

> This is the highest-quality build with the least hardware. If you only do one
> thing, do this.

---

## Build C — Standalone Raspberry Pi "gadget"

A small box you set on a tripod at the driving range or hitting net. It records,
processes, and serves the 3D viewer over its own Wi-Fi hotspot so you can review
swings on your phone.

### Bill of materials

| # | Part | Notes | ~Price |
|---|---|---|---|
| 1 | **Raspberry Pi 5 (4–8 GB)** | The brain. Pi 4 works but is slower. | $60–80 |
| 2 | **Global-shutter or high-fps camera** | *Best:* Raspberry Pi **Global Shutter Camera** (no motion smear). *Good & cheap:* Pi **Camera Module 3** (up to 120 fps at lower res). *Simplest:* a **1080p60 USB webcam**. | $25–50 |
| 3 | **Camera lens** (if using the Global Shutter cam) | 6 mm CS-mount covers a golfer at ~3–4 m. | $15 |
| 4 | **microSD card, 32 GB+ (A2 speed)** | Operating system + swing storage. | $8 |
| 5 | **USB-C power** | A wall plug at home, or a **USB-C power bank (PD, ≥27 W)** at the range. | $15–40 |
| 6 | **Active cooler / heatsink+fan** | Pose AI runs the CPU hot. Keep it cool. | $5–10 |
| 7 | **Case** | Any Pi 5 case with a camera-cable slot. | $10 |
| 8 | **Camera tripod + Pi/phone tripod mount** | Steady framing at hip/chest height. | $15–30 |
| 9 | *(optional)* small **HDMI touchscreen** | For a screen on the device itself; otherwise go headless. | $30–60 |

### Wiring / assembly

1. **Cooler onto the Pi.** Peel the thermal pad, clip the active cooler onto the
   Pi 5, plug its fan into the `FAN` header. (Do this first — it's fiddly once
   the camera cable is in.)
2. **Camera → Pi.**
   - *Ribbon camera (Global Shutter / Module 3):* gently lift the black clip on
     the Pi's **CAM/DISP** connector, slide the ribbon in **blue tab facing the
     USB ports**, press the clip down. Connect the other end to the camera board
     the same way.
   - *USB webcam:* just plug it into any USB port. No ribbon needed.
3. **microSD** into the slot on the underside.
4. **Assemble the case**, leaving the camera facing out and the vents clear.
5. **Power** via USB-C last.

```
        ┌──────────────────────────┐
        │  Raspberry Pi 5          │
        │  ┌───────┐               │
 CAM ───┼─▶│ CAM/  │  [active      │◀── USB-C power (wall or power bank)
 ribbon │  │ DISP  │   cooler/fan] │
        │  └───────┘               │◀── (USB webcam plugs in here instead)
        │  microSD ▄               │
        └──────────────────────────┘
                 │
         Camera on tripod, hip/chest height, 3–4 m from golfer
```

### Software setup on the Pi

1. Flash **Raspberry Pi OS (64-bit, Bookworm)** to the SD card with Raspberry Pi
   Imager. In the imager's settings, preset your Wi-Fi and enable SSH.
2. Boot, then:
   ```bash
   sudo apt update && sudo apt install -y python3-pip python3-opencv git
   git clone <this-repo-url>
   cd golf_swing_analyzer
   pip install -r requirements.txt --break-system-packages
   ```
   > If `mediapipe` won't install on the Pi, use Build C in "record-then-process"
   > mode: capture video with `libcamera-vid`/a USB cam, then run
   > `python capture.py --source clip.mp4 --complexity 0 --no-window`.
3. **Record headless** (no monitor):
   ```bash
   python capture.py --complexity 0 --no-window --duration 6
   ```
   Use `--complexity 0` — the fast pose model — so the Pi keeps up.
4. **Review from your phone.** Start the server bound to all interfaces:
   ```bash
   python server.py --host 0.0.0.0 --no-open
   ```
   On your phone's browser go to `http://<pi-ip-address>:8000/viewer/`.
   (Find the Pi's IP with `hostname -I`.)

### Make it turn-key (optional)

- **Auto-start on boot:** add a `systemd` service that runs `server.py` so the
  device is ready the moment it powers on.
- **Its own Wi-Fi hotspot:** configure the Pi as an access point (e.g. with
  NetworkManager's hotspot mode) so it works at a range with no internet. Note
  the 3D viewer loads the `three.js` library from a CDN the first time; either
  keep internet for the first load (browsers then cache it) or vendor `three.js`
  locally into `viewer/` for fully-offline use.
- **A physical button** on a GPIO pin to start/stop a recording, so you never
  touch a keyboard between swings.

---

## Build D — iPhone Pro LiDAR app (most accurate 3D)

Every build above uses a single flat camera, so it *guesses* how far each joint
is from the lens. A **Pro iPhone** (12 Pro and newer) has a **LiDAR scanner** that
*measures* real distance, so the depth is real instead of estimated. Apple's
ARKit turns that into a full 3D skeleton for you.

There's no wiring — the "hardware" is just your phone on a tripod. The work is a
one-time app build in **Xcode on a Mac**. Everything you need (source code +
step-by-step instructions) is in **[`ios/README.md`](ios/README.md)**.

Trade-off to know: LiDAR body tracking runs ~30–60 fps, so for the ultra-fast
moment of impact, a slow-mo clip (Build B) still freezes it better. Many people
use Build D for the 3D body motion and a slow-mo clip for impact. The app saves
the same `swing.json`, so both play back in the same 3D viewer.

## Where to place the camera (all builds)

Two classic golf angles — pick either, then rotate freely in 3D during review:

```
   FACE-ON                          DOWN-THE-LINE
   (camera in front)                (camera behind, along target line)

        📷                                    target
        │                                       ▲
        │  ~3-4 m                               │
        ▼                                       │
      🧍‍♂️ golfer                         🧍‍♂️──📷  ~3-4 m behind, on the
                                                target line
```

- Height: **hip to chest** (a tripod at ~1.1 m).
- Distance: **~3–4 m (10–13 ft)** — enough that the whole swing arc stays in frame.
- Keep the background simple and the golfer well-lit and higher-contrast than
  what's behind them.

That's it — build any version, run `capture.py`, then `server.py`, and study your
swing in 3D. Happy swinging. ⛳
