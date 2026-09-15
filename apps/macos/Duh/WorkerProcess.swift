//
//  WorkerProcess.swift
//  Duh
//

import Foundation

enum WorkerEvent {
    case status(message: String, device: String?, index: Int?)
    case transcript(id: String, text: String, tMs: Int, isFinal: Bool)
    case card(term: String, kind: String, blurb: String, confidence: Double, shownAtMs: Int, ttlMs: Int)
    case error(message: String)
    case clear
    case device(index: Int, name: String, refused: Bool)
    case unknown
}

enum WorkerProcessError: LocalizedError {
    case missingExecutable(String)
    case launchFailed(String)

    var errorDescription: String? {
        switch self {
        case let .missingExecutable(path):
            return "Worker not found at \(path). Run pip install -e \".[dev,live]\" in the repo."
        case let .launchFailed(message):
            return message
        }
    }
}

final class WorkerProcess {
    var onEvent: ((WorkerEvent) -> Void)?
    var onStateChange: ((Bool, String?) -> Void)?

    private var process: Process?
    private var stdoutPipe: Pipe?
    private let queue = DispatchQueue(label: "com.duh.worker.stdout")

    func start(executablePath: String, device: String) throws {
        stop()

        let url = URL(fileURLWithPath: executablePath)
        guard FileManager.default.isExecutableFile(atPath: url.path) else {
            throw WorkerProcessError.missingExecutable(executablePath)
        }

        let process = Process()
        process.executableURL = url
        process.arguments = ["--device", device]

        var env = ProcessInfo.processInfo.environment
        // Prefer repo .env via worker's _load_dotenv when cwd is repo root.
        let repoRoot = url.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        process.currentDirectoryURL = repoRoot

        if env["GROQ_API_KEY"] == nil || env["GROQ_API_KEY"]?.isEmpty == true {
            if let fromDotEnv = loadDotEnvValue(key: "GROQ_API_KEY", repoRoot: repoRoot) {
                env["GROQ_API_KEY"] = fromDotEnv
            }
        }
        process.environment = env

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = Pipe()
        stdoutPipe = pipe

        process.terminationHandler = { [weak self] proc in
            DispatchQueue.main.async {
                self?.onStateChange?(false, "Exited (\(proc.terminationStatus))")
            }
        }

        do {
            try process.run()
        } catch {
            throw WorkerProcessError.launchFailed(error.localizedDescription)
        }

        self.process = process
        onStateChange?(true, "Running")
        readStdout(pipe: pipe)
    }

    func stop() {
        guard let process else { return }
        if process.isRunning {
            process.terminate()
            process.waitUntilExit()
        }
        self.process = nil
        stdoutPipe = nil
        onStateChange?(false, "Stopped")
    }

    private func readStdout(pipe: Pipe) {
        let handle = pipe.fileHandleForReading
        queue.async { [weak self] in
            var buffer = Data()
            while true {
                let chunk = handle.availableData
                if chunk.isEmpty {
                    break
                }
                buffer.append(chunk)
                while let range = buffer.range(of: Data([0x0A])) {
                    let lineData = buffer.subdata(in: buffer.startIndex..<range.lowerBound)
                    buffer.removeSubrange(buffer.startIndex..<range.upperBound)
                    if let line = String(data: lineData, encoding: .utf8),
                       !line.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                       let event = Self.parseLine(line) {
                        self?.onEvent?(event)
                    }
                }
            }
        }
    }

    static func parseLine(_ line: String) -> WorkerEvent? {
        guard let data = line.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = obj["type"] as? String
        else {
            return nil
        }

        switch type {
        case "status":
            return .status(
                message: obj["message"] as? String ?? "",
                device: obj["device"] as? String,
                index: obj["index"] as? Int
            )
        case "transcript":
            return .transcript(
                id: obj["id"] as? String ?? "",
                text: obj["text"] as? String ?? "",
                tMs: obj["t_ms"] as? Int ?? 0,
                isFinal: obj["is_final"] as? Bool ?? true
            )
        case "card":
            return .card(
                term: obj["term"] as? String ?? "",
                kind: obj["kind"] as? String ?? "other",
                blurb: obj["blurb"] as? String ?? "",
                confidence: obj["confidence"] as? Double ?? 0,
                shownAtMs: obj["shown_at_ms"] as? Int ?? 0,
                ttlMs: obj["ttl_ms"] as? Int ?? 15_000
            )
        case "error":
            return .error(message: obj["message"] as? String ?? "unknown error")
        case "clear":
            return .clear
        case "device":
            return .device(
                index: obj["index"] as? Int ?? 0,
                name: obj["name"] as? String ?? "",
                refused: obj["refused"] as? Bool ?? false
            )
        default:
            return .unknown
        }
    }

    private func loadDotEnvValue(key: String, repoRoot: URL) -> String? {
        let envURL = repoRoot.appendingPathComponent(".env")
        guard let text = try? String(contentsOf: envURL, encoding: .utf8) else {
            return nil
        }
        for rawLine in text.split(whereSeparator: \.isNewline) {
            let line = rawLine.trimmingCharacters(in: .whitespaces)
            if line.isEmpty || line.hasPrefix("#") { continue }
            let parts = line.split(separator: "=", maxSplits: 1).map(String.init)
            guard parts.count == 2, parts[0] == key else { continue }
            return parts[1].trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))
        }
        return nil
    }
}
