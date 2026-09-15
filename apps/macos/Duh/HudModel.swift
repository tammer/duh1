//
//  HudModel.swift
//  Duh
//

import Combine
import Foundation

struct HudCardItem: Identifiable, Equatable {
    let id: String
    let term: String
    let kind: String
    let blurb: String
    let confidence: Double
    let shownAtMs: Int
}

@MainActor
final class HudModel: ObservableObject {
    @Published var cards: [HudCardItem] = []
    @Published var latestTranscript: String = ""
    @Published var statusText: String = "Idle"
    @Published var isRunning: Bool = false
    @Published var deviceName: String
    @Published var workerPath: String
    @Published var errorText: String = ""

    private let worker = WorkerProcess()

    init() {
        let defaults = UserDefaults.standard
        deviceName = defaults.string(forKey: "deviceName") ?? "BlackHole 2ch"
        if let saved = defaults.string(forKey: "workerPath"), !saved.isEmpty {
            workerPath = saved
        } else {
            workerPath = HudModel.defaultWorkerPath()
        }
        worker.onEvent = { [weak self] event in
            Task { @MainActor in
                self?.handle(event)
            }
        }
        worker.onStateChange = { [weak self] running, message in
            Task { @MainActor in
                self?.isRunning = running
                if let message, !message.isEmpty {
                    self?.statusText = message
                } else if !running {
                    self?.statusText = "Stopped"
                }
            }
        }
    }

    static func defaultWorkerPath() -> String {
        // apps/macos/Duh → repo root → .venv/bin/duh-worker
        let thisFile = URL(fileURLWithPath: #filePath)
        let repoRoot = thisFile
            .deletingLastPathComponent() // Duh/
            .deletingLastPathComponent() // macos/
            .deletingLastPathComponent() // apps/
            .deletingLastPathComponent() // repo
        return repoRoot.appendingPathComponent(".venv/bin/duh-worker").path
    }

    func start() {
        errorText = ""
        persistSettings()
        statusText = "Starting…"
        do {
            try worker.start(executablePath: workerPath, device: deviceName)
            isRunning = true
        } catch {
            errorText = error.localizedDescription
            statusText = "Failed to start"
            isRunning = false
        }
    }

    func stop() {
        worker.stop()
        isRunning = false
        statusText = "Stopped"
    }

    func persistSettings() {
        let defaults = UserDefaults.standard
        defaults.set(deviceName, forKey: "deviceName")
        defaults.set(workerPath, forKey: "workerPath")
    }

    private func handle(_ event: WorkerEvent) {
        switch event {
        case let .status(message, device, _):
            if let device {
                statusText = "\(message) · \(device)"
            } else {
                statusText = message
            }
            errorText = ""
        case let .transcript(_, text, _, _):
            latestTranscript = text
        case let .card(term, kind, blurb, confidence, shownAtMs, _):
            let item = HudCardItem(
                id: "\(term.lowercased())-\(shownAtMs)",
                term: term,
                kind: kind,
                blurb: blurb,
                confidence: confidence,
                shownAtMs: shownAtMs
            )
            cards.removeAll { $0.term.caseInsensitiveCompare(term) == .orderedSame }
            cards.insert(item, at: 0)
        case let .error(message):
            errorText = message
            statusText = "Error"
        case .clear:
            cards.removeAll()
        case .device:
            break
        case .unknown:
            break
        }
    }
}
