#!/usr/bin/env python3
"""
generate_sample.py -- Makes a fake ("synthetic") golf swing so the 3D viewer
has something to show before you record a real one.

This is NOT computer vision. It's just math: we place a stick figure and rotate
its torso and arms through a back-swing, downswing, and follow-through, then
save the result in the exact same swing.json format that capture.py produces.

Run:
    python generate_sample.py
It writes viewer/sample_swing.json (the viewer auto-loads it on startup).
"""

import json
import math
import os

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
POSE_CONNECTIONS = [
    [11, 12], [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
    [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20],
    [11, 23], [12, 24], [23, 24],
    [23, 25], [25, 27], [27, 29], [27, 31], [29, 31],
    [24, 26], [26, 28], [28, 30], [28, 32], [30, 32],
    [0, 11], [0, 12],
]

N = 100          # frames
FPS = 30.0


# ---- tiny vector / rotation helpers (up-positive, meters) ----
def rot_x(v, a):
    x, y, z = v
    c, s = math.cos(a), math.sin(a)
    return (x, y * c - z * s, y * s + z * c)


def rot_y(v, a):
    x, y, z = v
    c, s = math.cos(a), math.sin(a)
    return (x * c + z * s, y, -x * s + z * c)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def smoothstep(a, b, t):
    t = max(0.0, min(1.0, t))
    t = t * t * (3 - 2 * t)
    return a + (b - a) * t


def keyed(keys, i):
    """Interpolate a value from (frame, value) keyframes with smoothstep."""
    if i <= keys[0][0]:
        return keys[0][1]
    if i >= keys[-1][0]:
        return keys[-1][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f0 <= i <= f1:
            return smoothstep(v0, v1, (i - f0) / (f1 - f0))
    return keys[-1][1]


# Motion curves (radians / meters), tuned to read as a real golf swing.
THETA_SH = [(0, 0.0), (10, 0.0), (44, 2.1), (50, 2.1), (57, 0.0), (100, -2.2)]
THETA_HIP = [(0, 0.0), (10, 0.0), (44, 0.9), (50, 0.9), (57, -0.2), (100, -1.3)]
BETA = [(0, 0.5), (10, 0.5), (46, 2.25), (52, 2.2), (57, 0.55), (70, 1.6), (100, 2.6)]
SWAY = [(0, 0.0), (44, 0.03), (57, -0.04), (100, -0.06)]


def build_frame(i):
    th_sh = keyed(THETA_SH, i)
    th_hip = keyed(THETA_HIP, i)
    beta = keyed(BETA, i)
    sway = keyed(SWAY, i)
    hip_c = (sway, 0.0, 0.0)          # hip center (weight shift)
    sh_c = (sway, 0.55, 0.0)          # shoulder center

    # Arm assembly: rotate local arm points by Rx(beta) then Ry(shoulder turn).
    def arm(local):
        return add(sh_c, rot_y(rot_x(local, beta), th_sh))

    pts = [None] * 33

    # Shoulders (turn about vertical through hip center)
    pts[11] = add(hip_c, rot_y((-0.20, 0.55, 0.0), th_sh))
    pts[12] = add(hip_c, rot_y((0.20, 0.55, 0.0), th_sh))
    # Hips (turn less)
    pts[23] = add(hip_c, rot_y((-0.12, 0.0, 0.0), th_hip))
    pts[24] = add(hip_c, rot_y((0.12, 0.0, 0.0), th_hip))

    # Arms
    pts[13] = arm((-0.16, -0.28, 0.14))   # left elbow
    pts[14] = arm((0.16, -0.28, 0.14))    # right elbow
    pts[15] = arm((-0.05, -0.50, 0.27))   # left wrist
    pts[16] = arm((0.05, -0.50, 0.27))    # right wrist
    # hand detail points near the wrists
    pts[17] = arm((-0.06, -0.55, 0.29))   # left pinky
    pts[19] = arm((-0.04, -0.56, 0.30))   # left index
    pts[21] = arm((-0.03, -0.53, 0.28))   # left thumb
    pts[18] = arm((0.06, -0.55, 0.29))    # right pinky
    pts[20] = arm((0.04, -0.56, 0.30))    # right index
    pts[22] = arm((0.03, -0.53, 0.28))    # right thumb

    # Legs (mostly still; a little athletic flex)
    pts[25] = add(hip_c, (-0.14, -0.46, 0.05))   # left knee
    pts[26] = add(hip_c, (0.14, -0.46, 0.05))    # right knee
    pts[27] = (-0.15, -0.92, 0.02)               # left ankle
    pts[28] = (0.15, -0.92, 0.02)                # right ankle
    pts[29] = (-0.15, -0.94, -0.04)              # left heel
    pts[30] = (0.15, -0.94, -0.04)               # right heel
    pts[31] = (-0.15, -0.95, 0.12)               # left foot index
    pts[32] = (0.15, -0.95, 0.12)                # right foot index

    # Head (turns only slightly, like a real golfer keeping their head still)
    head_turn = th_sh * 0.12
    nose = add(sh_c, rot_y((0.0, 0.24, 0.11), head_turn))
    pts[0] = nose
    pts[1] = add(nose, (-0.03, 0.02, 0.02))
    pts[2] = add(nose, (-0.04, 0.02, 0.02))
    pts[3] = add(nose, (-0.05, 0.02, 0.02))
    pts[4] = add(nose, (0.03, 0.02, 0.02))
    pts[5] = add(nose, (0.04, 0.02, 0.02))
    pts[6] = add(nose, (0.05, 0.02, 0.02))
    pts[7] = add(nose, (-0.07, 0.0, -0.04))
    pts[8] = add(nose, (0.07, 0.0, -0.04))
    pts[9] = add(nose, (-0.03, -0.05, 0.02))
    pts[10] = add(nose, (0.03, -0.05, 0.02))

    # Convert up-positive (x,up,fwd) -> MediaPipe world (x, y=down, z=toward-cam)
    # stored_y = -up ; stored_z = -fwd  (so the viewer stands it up, facing you)
    landmarks = []
    for p in pts:
        landmarks.append([round(p[0], 5), round(-p[1], 5), round(-p[2], 5), 0.99])
    return {"t": round(i / FPS, 4), "landmarks": landmarks}


def main():
    frames = [build_frame(i) for i in range(N)]
    data = {
        "meta": {
            "created": "synthetic",
            "name": "sample_swing (demo)",
            "source": "generate_sample.py",
            "fps": FPS,
            "frame_count": N,
            "model_complexity": -1,
            "landmark_names": LANDMARK_NAMES,
            "connections": POSE_CONNECTIONS,
            "coordinate_system": "mediapipe_world: x=right, y=down, z=toward-camera, meters",
            "note": "Synthetic demo swing (not a real capture).",
        },
        "frames": frames,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer", "sample_swing.json")
    with open(out, "w") as f:
        json.dump(data, f)
    print(f"Wrote {out}  ({N} frames)")


if __name__ == "__main__":
    main()
