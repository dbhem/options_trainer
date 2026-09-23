//  ARViewContainer.swift
//  Turns on the rear camera + ARKit body tracking, and feeds every detected
//  3D skeleton to the SwingRecorder. LiDAR (on Pro iPhones) is used automatically
//  by ARKit here to make the depth and body tracking more accurate.
//
//  This is a thin SwiftUI wrapper around ARKit's RealityKit view (ARView).

import SwiftUI
import RealityKit
import ARKit

struct ARViewContainer: UIViewRepresentable {
    let recorder: SwingRecorder

    func makeCoordinator() -> Coordinator { Coordinator(recorder: recorder) }

    func makeUIView(context: Context) -> ARView {
        let view = ARView(frame: .zero)
        view.session.delegate = context.coordinator

        // ARBodyTrackingConfiguration = Apple's 3D motion capture.
        let config = ARBodyTrackingConfiguration()
        config.automaticSkeletonScaleEstimationEnabled = true
        view.session.run(config, options: [.resetTracking, .removeExistingAnchors])
        return view
    }

    func updateUIView(_ uiView: ARView, context: Context) {}

    // The Coordinator receives frame-by-frame updates from ARKit.
    final class Coordinator: NSObject, ARSessionDelegate {
        let recorder: SwingRecorder
        init(recorder: SwingRecorder) { self.recorder = recorder }

        func session(_ session: ARSession, didUpdate anchors: [ARAnchor]) {
            for anchor in anchors {
                if let body = anchor as? ARBodyAnchor {
                    recorder.capture(body.skeleton)
                }
            }
        }
    }
}
