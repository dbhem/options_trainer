//  SwingRecorder.swift
//  Collects the 3D skeleton for every frame while you're recording, then writes
//  it out as swing.json -- the SAME file format the 3D viewer already reads.
//
//  ARKit hands us each joint as a position in meters, measured from the hips
//  (the "root"). That's exactly how MediaPipe's world coordinates work, so the
//  data lines up. The only fix-up: ARKit's Y axis points UP, while our format
//  (MediaPipe) points Y DOWN, so we flip the sign of Y. The viewer flips it back
//  and stands the figure upright.

import ARKit
import simd

final class SwingRecorder: ObservableObject {

    @Published var isRecording = false
    @Published var frameCount = 0

    private var frames: [(t: Double, lm: [[Double]])] = []
    private var startTime: Double = 0
    private let def = ARSkeletonDefinition.defaultBody3D

    // Cache: our 33 indices -> ARKit joint index (looked up once).
    private lazy var arkitIndex: [Int?] = MP.arkitName.map { name in
        guard let name = name else { return nil }
        return def.jointNames.firstIndex(of: name)
    }

    func start() {
        frames.removeAll()
        startTime = CACurrentMediaTime()
        DispatchQueue.main.async { self.frameCount = 0; self.isRecording = true }
    }

    func stop() {
        DispatchQueue.main.async { self.isRecording = false }
    }

    /// Called ~30-60x per second by the AR session while recording.
    func capture(_ skeleton: ARSkeleton3D) {
        guard isRecording else { return }
        let t = CACurrentMediaTime() - startTime
        let transforms = skeleton.jointModelTransforms

        var pos = [SIMD3<Float>](repeating: .zero, count: 33)
        var vis = [Double](repeating: -1, count: 33)  // -1 = needs fallback

        // Pass 1: read every point that maps to a real ARKit joint.
        for i in 0..<33 {
            if let idx = arkitIndex[i], idx < transforms.count {
                let c = transforms[idx].columns.3   // translation = joint position
                pos[i] = SIMD3<Float>(c.x, c.y, c.z)
                vis[i] = skeleton.isJointTracked(idx) ? 0.99 : 0.4
            }
        }
        // Pass 2: anything without an ARKit joint borrows its parent's spot.
        for i in 0..<33 where vis[i] < 0 {
            pos[i] = pos[MP.parent[i]]
            vis[i] = 0.5
        }

        // ARKit (x right, y UP, z toward camera)  ->  MediaPipe world (y DOWN).
        // If the figure ever appears lying down or mirrored in the viewer, this
        // single line is where you'd tweak the axis signs.
        var lm = [[Double]]()
        lm.reserveCapacity(33)
        for i in 0..<33 {
            let v = pos[i]
            lm.append([r5(v.x), r5(-v.y), r5(v.z), r3(vis[i])])
        }

        frames.append((t, lm))
        DispatchQueue.main.async { self.frameCount = self.frames.count }
    }

    /// Write swing.json into the app's Documents folder and return its URL,
    /// so the Record screen can hand it to the iOS share sheet (AirDrop, Files…).
    func export() -> URL? {
        guard frames.count > 1 else { return nil }

        let span = frames.last!.t - frames.first!.t
        let fps = span > 0 ? Double(frames.count - 1) / span : 30.0

        let meta: [String: Any] = [
            "created": ISO8601DateFormatter().string(from: Date()),
            "name": "ios_swing_\(Int(Date().timeIntervalSince1970))",
            "source": "iPhone ARKit body tracking (LiDAR-assisted)",
            "fps": (fps * 1000).rounded() / 1000,
            "frame_count": frames.count,
            "model_complexity": -2,
            "landmark_names": MP.names,
            "connections": MP.connections,
            "coordinate_system":
                "arkit->mediapipe_world: x=right, y=down, z=toward-camera, meters, origin=hips",
            "note": "Captured on iPhone using ARKit 3D body tracking.",
        ]
        let frameObjs: [[String: Any]] = frames.map {
            ["t": (($0.t * 10000).rounded() / 10000), "landmarks": $0.lm]
        }
        let root: [String: Any] = ["meta": meta, "frames": frameObjs]

        guard let data = try? JSONSerialization.data(withJSONObject: root) else { return nil }
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let url = dir.appendingPathComponent("\(meta["name"] as! String).json")
        do {
            try data.write(to: url)
            return url
        } catch {
            return nil
        }
    }

    private func r5(_ x: Float) -> Double { (Double(x) * 100000).rounded() / 100000 }
    private func r3(_ x: Double) -> Double { (x * 1000).rounded() / 1000 }
}
