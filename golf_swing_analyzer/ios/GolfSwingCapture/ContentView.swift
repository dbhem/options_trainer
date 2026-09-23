//  ContentView.swift
//  The screen you see: the live camera, a REC status, and one big button that
//  starts/stops recording. When you stop, it saves swing.json and pops up the
//  iOS share sheet so you can AirDrop it to your Mac or save it to Files.

import SwiftUI
import ARKit

struct ContentView: View {
    @StateObject private var recorder = SwingRecorder()
    @State private var shareURL: URL?
    @State private var showShare = false

    private let supported = ARBodyTrackingConfiguration.isSupported

    var body: some View {
        ZStack {
            if supported {
                ARViewContainer(recorder: recorder)
                    .edgesIgnoringSafeArea(.all)

                VStack {
                    // Status pill (top-left)
                    HStack {
                        Text(recorder.isRecording
                             ? "● REC   \(recorder.frameCount) frames"
                             : "Ready — stand back so your whole body fits")
                            .font(.subheadline).bold()
                            .padding(.horizontal, 12).padding(.vertical, 8)
                            .background(.black.opacity(0.55))
                            .foregroundColor(recorder.isRecording ? .red : .white)
                            .clipShape(Capsule())
                        Spacer()
                    }
                    .padding()

                    Spacer()

                    // Record / Stop button (bottom)
                    Button(action: toggle) {
                        Text(recorder.isRecording ? "Stop & Save" : "Record Swing")
                            .font(.title2).bold()
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(recorder.isRecording ? Color.red : Color.green)
                            .foregroundColor(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                    }
                    .padding()
                }
            } else {
                unsupportedView
            }
        }
        .sheet(isPresented: $showShare) {
            if let url = shareURL { ShareSheet(items: [url]) }
        }
    }

    private func toggle() {
        if recorder.isRecording {
            recorder.stop()
            if let url = recorder.export() {
                shareURL = url
                showShare = true
            }
        } else {
            recorder.start()
        }
    }

    private var unsupportedView: some View {
        VStack(spacing: 14) {
            Image(systemName: "figure.walk.motion").font(.system(size: 48))
            Text("3D body tracking isn't supported on this device.")
                .font(.headline).multilineTextAlignment(.center)
            Text("Needs an iPhone/iPad with an A12 Bionic chip or newer (iPhone XS and up). Pro models add a LiDAR scanner, which makes depth more accurate.")
                .font(.subheadline).foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(28)
    }
}

// Wraps the standard iOS "share" popup so we can hand off the saved file.
struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ vc: UIActivityViewController, context: Context) {}
}
