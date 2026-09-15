//
//  HudRootView.swift
//  Duh
//

import AppKit
import SwiftUI

struct HudRootView: View {
    @ObservedObject var model: HudModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Duh")
                    .font(.title2.weight(.semibold))
                Spacer()
                Circle()
                    .fill(model.isRunning ? Color.green : Color.secondary.opacity(0.4))
                    .frame(width: 8, height: 8)
                Text(model.isRunning ? "Live" : "Idle")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text("Route system output through a Multi-Output Device that includes BlackHole and your speakers.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            TextField("Capture device", text: $model.deviceName)
                .textFieldStyle(.roundedBorder)
                .disabled(model.isRunning)

            TextField("Worker path", text: $model.workerPath)
                .textFieldStyle(.roundedBorder)
                .disabled(model.isRunning)
                .font(.system(.caption, design: .monospaced))

            HStack {
                Button(model.isRunning ? "Stop" : "Start") {
                    if model.isRunning {
                        model.stop()
                    } else {
                        model.start()
                    }
                }
                .keyboardShortcut(.defaultAction)

                Text(model.statusText)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)

                Spacer()

                Button("Quit") {
                    model.stop()
                    NSApp.terminate(nil)
                }
            }

            if !model.errorText.isEmpty {
                Text(model.errorText)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if !model.latestTranscript.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Transcript")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    Text(model.latestTranscript)
                        .font(.callout)
                        .lineLimit(3)
                }
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.primary.opacity(0.05), in: RoundedRectangle(cornerRadius: 8))
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("HUD")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                if model.cards.isEmpty {
                    Text("Cards will appear when jargon is detected.")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(model.cards) { card in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack(alignment: .firstTextBaseline) {
                                Text(card.term)
                                    .font(.headline)
                                Text(card.kind)
                                    .font(.caption2)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Color.accentColor.opacity(0.15), in: Capsule())
                            }
                            Text(card.blurb)
                                .font(.callout)
                                .foregroundStyle(.primary.opacity(0.9))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.primary.opacity(0.06), in: RoundedRectangle(cornerRadius: 10))
                    }
                }
            }

            Spacer(minLength: 0)
        }
        .padding(16)
        .frame(minWidth: 300, minHeight: 280)
    }
}

struct SettingsView: View {
    @ObservedObject var model: HudModel

    var body: some View {
        Form {
            TextField("Worker path", text: $model.workerPath)
            TextField("Device", text: $model.deviceName)
            Button("Save") {
                model.persistSettings()
            }
        }
        .padding()
        .frame(width: 480)
    }
}
