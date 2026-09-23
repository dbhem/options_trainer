//  MediaPipeMapping.swift
//  The "translator."
//
//  Apple's ARKit gives us a big skeleton (~90 joints with its own names).
//  Our 3D viewer expects the smaller 33-point layout that the Python capture
//  tool (MediaPipe) produces. This file is just the lookup table that says
//  "Apple's left_hand_joint IS our point #15 (left_wrist)", and so on -- plus
//  the same bone list and point names the viewer already knows.
//
//  Because we output the identical format, a swing recorded on the iPhone plays
//  back in the same viewer as one recorded with a webcam. No viewer changes.

import Foundation

enum MP {

    /// The 33 point names, in order, exactly matching capture.py / the viewer.
    static let names: [String] = [
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

    /// Which points connect to which (the "bones"), same as the viewer.
    static let connections: [[Int]] = [
        [11, 12], [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
        [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20],
        [11, 23], [12, 24], [23, 24],
        [23, 25], [25, 27], [27, 29], [27, 31], [29, 31],
        [24, 26], [26, 28], [28, 30], [28, 32], [30, 32],
        [0, 11], [0, 12],
    ]

    /// For each of our 33 points, the ARKit joint name to read it from.
    /// `nil` means ARKit has no matching joint -> we borrow the parent's spot
    /// (see `parent` below) so nothing draws a bone off into space.
    ///
    /// ARKit joint names come from ARSkeletonDefinition.defaultBody3D. If a name
    /// here isn't found on a given iOS version, the code falls back gracefully.
    static let arkitName: [String?] = [
        "nose_joint",              // 0  nose
        "left_eye_joint",          // 1  left_eye_inner
        "left_eye_joint",          // 2  left_eye
        "left_eye_joint",          // 3  left_eye_outer
        "right_eye_joint",         // 4  right_eye_inner
        "right_eye_joint",         // 5  right_eye
        "right_eye_joint",         // 6  right_eye_outer
        "head_joint",              // 7  left_ear (approx)
        "head_joint",              // 8  right_ear (approx)
        "jaw_joint",               // 9  mouth_left (approx)
        "jaw_joint",               // 10 mouth_right (approx)
        "left_shoulder_1_joint",   // 11 left_shoulder
        "right_shoulder_1_joint",  // 12 right_shoulder
        "left_forearm_joint",      // 13 left_elbow
        "right_forearm_joint",     // 14 right_elbow
        "left_hand_joint",         // 15 left_wrist
        "right_hand_joint",        // 16 right_wrist
        "left_handPinkyStart_joint",  // 17 left_pinky
        "right_handPinkyStart_joint", // 18 right_pinky
        "left_handIndexStart_joint",  // 19 left_index
        "right_handIndexStart_joint", // 20 right_index
        "left_handThumbStart_joint",  // 21 left_thumb
        "right_handThumbStart_joint", // 22 right_thumb
        "left_upLeg_joint",        // 23 left_hip
        "right_upLeg_joint",       // 24 right_hip
        "left_leg_joint",          // 25 left_knee
        "right_leg_joint",         // 26 right_knee
        "left_foot_joint",         // 27 left_ankle
        "right_foot_joint",        // 28 right_ankle
        "left_foot_joint",         // 29 left_heel (approx = ankle)
        "right_foot_joint",        // 30 right_heel (approx = ankle)
        "left_toes_joint",         // 31 left_foot_index
        "right_toes_joint",        // 32 right_foot_index
    ]

    /// When an ARKit joint isn't available, copy this parent point's position
    /// instead (so, e.g., a missing finger sits on the wrist, not at the hips).
    static let parent: [Int] = [
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,   // face points -> nose
        11, 12, 11, 12,                    // shoulders/elbows -> self-ish
        15, 16,                            // wrists -> self
        15, 16, 15, 16, 15, 16,            // fingers -> nearest wrist
        23, 24, 23, 24, 27, 28, 27, 28,    // legs -> nearest parent
        27, 28,                            // toes -> ankle
    ]
}
