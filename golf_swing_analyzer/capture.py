#!/usr/bin/env python3
"""
capture.py  --  The "eyes" of the golf swing analyzer.

What it does, in plain words
----------------------------
1. Opens your camera (a laptop webcam, a USB webcam, or a Raspberry Pi camera).
2. For every picture (frame) the camera takes, it asks a "pose AI" (Google's
   MediaPipe) where your body joints are -- shoulders, elbows, wrists, hips,
   knees, ankles, and so on. Think of it as connect-the-dots for your body.
3. MediaPipe gives us those dots in real 3D (meters), so we can rebuild the
   swing as a little stick figure you can spin around later.
4. We save every frame's dots into a file called swing.json, and (optionally)
   also save the plain video.

You then open the 3D viewer (see ../viewer) and play the swing back frame by
frame, rotating it however you like.

Basic use
---------
    python capture.py                 # use camera 0, press 'q' to stop
    python capture.py --duration 6    # record ~6 seconds then stop
    python capture.py --source 1      # use a second/USB camera
    python capture.py --source swing.mp4   # analyze an existing video file
    python capture.py --output ./swings    # where to save results

Tip: a golf swing is FAST. If your video looks smeared/blurry, the AI will
guess badly. Use a camera that can do 60 frames-per-second if you can, add
light, and stand far enough back that your whole body fits in the picture.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

# ---- The 33 body points MediaPipe tracks, in order (index 0..32). ----------
# We store the names so the viewer is self-contained and never has to guess.
LANDMARK_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky",
    "left_index", "right_index", "left_thumb", "right_thumb",
    "left_hip", "right_hip", "left_knee", "right_knee",
    "left_ankle", "right_ankle", "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]

# Which dots connect to which, so the viewer can draw "bones" (lines).
# These are the standard MediaPipe pose connections.
POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),
    # a few face/torso links so the head isn't floating
    (0, 11), (0, 12),
]


def parse_source(raw):
    """A camera source can be a number (0, 1, ...) or a video file path."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return raw


def main():
    ap = argparse.ArgumentParser(description="Capture a golf swing as a 3D skeleton.")
    ap.add_argument("--source", default="0",
                    help="Camera index (0,1,...) or a video file path. Default: 0")
    ap.add_argument("--output", default="swings",
                    help="Folder to save results into. Default: ./swings")
    ap.add_argument("--name", default=None,
                    help="Name for this swing. Default: a timestamp.")
    ap.add_argument("--duration", type=float, default=0.0,
                    help="Auto-stop after this many seconds. 0 = record until you press 'q'.")
    ap.add_argument("--complexity", type=int, choices=[0, 1, 2], default=1,
                    help="Pose model: 0=fast/rough (good on Raspberry Pi), "
                         "1=balanced (default), 2=slow/accurate.")
    ap.add_argument("--save-video", action="store_true",
                    help="Also save the raw camera video next to swing.json.")
    ap.add_argument("--no-window", action="store_true",
                    help="Don't show a preview window (use on headless devices).")
    ap.add_argument("--width", type=int, default=1280, help="Requested camera width.")
    ap.add_argument("--height", type=int, default=720, help="Requested camera height.")
    ap.add_argument("--fps", type=float, default=60.0, help="Requested camera FPS.")
    args = ap.parse_args()

    # Import heavy libraries here so `--help` works even if they're missing.
    try:
        import cv2
    except ImportError:
        sys.exit("ERROR: OpenCV is not installed. Run:  pip install -r requirements.txt")
    try:
        import mediapipe as mp
    except ImportError:
        sys.exit("ERROR: MediaPipe is not installed. Run:  pip install -r requirements.txt")

    source = parse_source(args.source)
    name = args.name or datetime.now().strftime("swing_%Y%m%d_%H%M%S")
    out_dir = os.path.join(args.output, name)
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(source)
    if isinstance(source, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        cap.set(cv2.CAP_PROP_FPS, args.fps)
    if not cap.isOpened():
        sys.exit(f"ERROR: could not open camera/video source: {args.source!r}")

    # What FPS did we actually get? (Cameras often ignore requests.)
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    if not src_fps or src_fps != src_fps or src_fps <= 1:  # 0, NaN, or nonsense
        src_fps = args.fps if isinstance(source, int) else 30.0

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        model_complexity=args.complexity,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    writer = None
    if args.save_video:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or args.width
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or args.height
        writer = cv2.VideoWriter(os.path.join(out_dir, "video.mp4"), fourcc,
                                 src_fps, (w, h))

    frames = []
    start = time.time()
    frame_idx = 0
    print(f"Recording '{name}'. Camera FPS ~= {src_fps:.0f}.")
    if not args.no_window:
        print("Press 'q' in the preview window to stop.")
    if args.duration > 0:
        print(f"Will auto-stop after {args.duration:.1f}s.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break  # camera unplugged or video ended
            t = time.time() - start

            # MediaPipe wants RGB; OpenCV gives BGR. Flip the colors.
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = pose.process(rgb)

            if results.pose_world_landmarks:
                lms = results.pose_world_landmarks.landmark
                frames.append({
                    "t": round(t, 4),
                    "landmarks": [[round(l.x, 5), round(l.y, 5), round(l.z, 5),
                                   round(l.visibility, 3)] for l in lms],
                })

            if writer is not None:
                writer.write(frame)

            if not args.no_window:
                # Draw the 2D skeleton on the preview so you can see it working.
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                cv2.putText(frame, f"REC {t:4.1f}s  frames:{len(frames)}",
                            (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                            (0, 0, 255), 2, cv2.LINE_AA)
                cv2.imshow("Golf Swing Capture (press q to stop)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            frame_idx += 1
            if args.duration > 0 and t >= args.duration:
                break
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        if not args.no_window:
            cv2.destroyAllWindows()
        pose.close()

    if not frames:
        sys.exit("No poses detected. Make sure your whole body is visible and lit.")

    # Work out the true average FPS from the timestamps we actually recorded.
    span = frames[-1]["t"] - frames[0]["t"]
    true_fps = (len(frames) - 1) / span if span > 0 else src_fps

    data = {
        "meta": {
            "created": datetime.now().isoformat(timespec="seconds"),
            "name": name,
            "source": str(args.source),
            "fps": round(true_fps, 3),
            "frame_count": len(frames),
            "model_complexity": args.complexity,
            "landmark_names": LANDMARK_NAMES,
            "connections": [list(c) for c in POSE_CONNECTIONS],
            "coordinate_system": (
                "mediapipe_world: x=right, y=down, z=toward-camera, "
                "meters, origin ~= midpoint of hips"
            ),
        },
        "frames": frames,
    }

    out_path = os.path.join(out_dir, "swing.json")
    with open(out_path, "w") as f:
        json.dump(data, f)

    print(f"\nDone. {len(frames)} frames over {span:.2f}s (~{true_fps:.0f} fps).")
    print(f"Saved: {out_path}")
    if writer is not None:
        print(f"Saved: {os.path.join(out_dir, 'video.mp4')}")
    print("\nNow view it in 3D:")
    print(f"    python server.py")
    print("  then open the printed link and load this swing.")


if __name__ == "__main__":
    main()
