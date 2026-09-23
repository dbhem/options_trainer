# 📱 iPhone LiDAR Capture (ARKit 3D Body Tracking)

This is a small iOS app that records your golf swing as a **real 3D skeleton**
using ARKit body tracking (helped by the **LiDAR** scanner on Pro iPhones). It
saves a `swing.json` in the **exact same format** as the webcam tool — so it
plays back in the same 3D viewer with no changes.

Why this is better than the webcam version: a single webcam has to *guess*
depth. Here the phone **measures** it, so the toward/away axis is real, not
estimated.

---

## What you need

- A **Mac** with **Xcode** (free from the Mac App Store). ARKit apps can only be
  built with Xcode — there's no way around this, and it can't be built on Linux.
- A **physical iPhone or iPad** — ARKit does **not** run in the simulator.
  - **Body tracking** needs an **A12 Bionic chip or newer** (iPhone XS and up).
  - **LiDAR** (extra depth accuracy) is on **iPhone 12 Pro / Pro Max and newer
    Pro models**, and iPad Pro 2020+. Non-Pro phones still work — they just rely
    on the camera + motion instead of LiDAR.
- A free **Apple ID** (for "personal team" signing — no paid developer account
  needed to run on your own device).

> I wrote all the source code, but I can't compile or test it from here (no Mac).
> The steps below are the whole recipe; the app is deliberately tiny (5 files).

---

## Build it (about 10 minutes)

1. **New project:** open Xcode → *File ▸ New ▸ Project…* → **iOS ▸ App** → Next.
   - Product Name: `GolfSwingCapture`
   - Interface: **SwiftUI**, Language: **Swift**
   - Save it anywhere.

2. **Add the source files.** In Xcode's left sidebar, delete the auto-created
   `ContentView.swift` and the `...App.swift` file (move to trash), then
   drag **all five** `.swift` files from this folder
   (`golf_swing_analyzer/ios/GolfSwingCapture/`) into the project.
   ✔ Tick **"Copy items if needed"** and your app target.

   Files: `GolfSwingCaptureApp.swift`, `ContentView.swift`, `ARViewContainer.swift`,
   `SwingRecorder.swift`, `MediaPipeMapping.swift`.

3. **Camera permission text (required, or the app crashes on launch).**
   Select the project (top of sidebar) → your target → **Info** tab → add a row:
   - Key: **Privacy - Camera Usage Description**
     (`NSCameraUsageDescription`)
   - Value: `Used to record your golf swing in 3D.`

4. **Deployment target:** target → **General** → set **Minimum Deployments** to
   **iOS 15.0** (or higher).

5. **Signing:** target → **Signing & Capabilities** → check **Automatically
   manage signing** → pick your Apple ID under **Team** (add it if needed).

6. **Run on your device.** Plug in the iPhone/iPad (or use wireless), pick it in
   Xcode's device menu at the top, and press **▶ Run**. First run: on the phone,
   trust the developer profile under *Settings ▸ General ▸ VPN & Device
   Management*.

---

## Record a swing

1. Prop the phone on a tripod, **~3–4 m (10–13 ft)** away at hip/chest height,
   so your **whole body and the full club arc** are in view.
2. Open the app, stand in frame (it starts tracking when it sees your full body).
3. Tap **Record Swing**, make your swing, tap **Stop & Save**.
4. The iOS **share sheet** pops up with `swing.json`. **AirDrop** it to your Mac,
   or **Save to Files**.

## Play it back in 3D

Drop the file into the viewer you already have — two ways:

- **Easiest:** run `python server.py` in `golf_swing_analyzer/`, open the viewer,
  and **drag the `swing.json` straight onto the page**.
- **Or** put it at `golf_swing_analyzer/swings/<any-name>/swing.json` and it
  shows up in the viewer's dropdown.

Same viewer, same controls (play, step frame-by-frame, orbit, hand-path). The
skeleton will just be more accurate in depth than the webcam version.

---

## Good to know (the honest trade-offs)

- **Speed vs. depth.** ARKit body tracking runs ~**30–60 fps**. A downswing is
  extremely fast, so 60 fps is *okay* but not amazing at the moment of impact.
  Your phone's plain **slow-mo (120–240 fps)** freezes impact better but has no
  depth. Best of both worlds = use this app for the 3D body motion, and a
  separate slow-mo clip (fed to the webcam tool with `--source clip.mov`) for the
  split-second around impact.
- **Sunlight** weakens LiDAR. Indoors, a net, or shade give the cleanest data;
  its useful range is ~5 m.
- **One person** in frame, well-lit, higher-contrast than the background.

## Troubleshooting

- **App crashes immediately** → you skipped step 3 (camera permission text).
- **"body tracking not supported" screen** → the device is older than A12, or
  you're on the simulator (must use a real device).
- **Figure appears lying down / mirrored in the viewer** → adjust the axis signs
  on the marked line in `SwingRecorder.swift` (`[r5(v.x), r5(-v.y), r5(v.z), …]`).
  Different iOS versions have shifted the body coordinate frame before; that one
  line is the only place you'd change.
- **No `swing.json` appears** → make sure you actually saw the "REC … frames"
  count climbing; if it stayed at 0, the phone couldn't see your full body.

## Files in this folder

```
ios/
├── README.md                         (this file)
└── GolfSwingCapture/
    ├── GolfSwingCaptureApp.swift      app entry point
    ├── ContentView.swift             the screen + Record button + share sheet
    ├── ARViewContainer.swift         camera + ARKit body tracking
    ├── SwingRecorder.swift           collects frames -> writes swing.json
    └── MediaPipeMapping.swift        ARKit joints -> our 33-point format
```
