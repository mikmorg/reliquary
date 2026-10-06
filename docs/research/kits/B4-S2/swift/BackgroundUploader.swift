// Kit B4-S2 sketch. NOT COMPILED: the research container has no Apple SDK.
// Written against Apple's documented APIs (URLSessionConfiguration.background(withIdentifier:),
// uploadTask(with:fromFile:), handleEventsForBackgroundURLSession) and the B4-S1 core API
// (spikes/B4-S1/core/src/lib.rs, whose Swift bindings compiled and ran on Linux).
// Expect small fixes in Xcode. Record every change you had to make in the results.

import Foundation
import UIKit

/// One background session for the whole app (Apple: most apps need one; use a fixed identifier).
final class BackgroundUploader: NSObject, URLSessionDataDelegate, @unchecked Sendable {
    static let sessionId = "org.example.reliquary.b4s2.upload"   // replace with <bundle-id>.upload
    static let shared = BackgroundUploader()

    let core: Core
    private(set) lazy var session: URLSession = {
        let cfg = URLSessionConfiguration.background(withIdentifier: Self.sessionId)
        cfg.sessionSendsLaunchEvents = true          // relaunch the app in the background on completion
        cfg.isDiscretionary = false                  // record what happens; iOS forces true for tasks started in background
        cfg.allowsCellularAccess = false             // kit default: Wi-Fi only
        cfg.timeoutIntervalForResource = 7 * 24 * 3600
        return URLSession(configuration: cfg, delegate: self, delegateQueue: nil)
    }()
    var backgroundCompletionHandler: (() -> Void)?   // set from AppDelegate

    override init() {
        // Application Support, not Caches: iOS may purge Caches under disk pressure.
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("reliquary", isDirectory: true)
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        var spool = base.appendingPathComponent("spool", isDirectory: true)
        try? FileManager.default.createDirectory(at: spool, withIntermediateDirectories: true)
        var rv = URLResourceValues(); rv.isExcludedFromBackup = true
        try? spool.setResourceValues(rv)
        // File protection: spool + DB must be readable while the phone is locked after first unlock.
        try? (base as NSURL).setResourceValue(URLFileProtection.completeUntilFirstUserAuthentication,
                                              forKey: .fileProtectionKey)
        core = try! Core.open(dbPath: base.appendingPathComponent("core.sqlite").path,
                              spoolDir: spool.path,
                              spoolBudgetBytes: 2 * 1024 * 1024 * 1024,   // BUD-TMP cap; lower it for the test
                              chunksPerPart: 80)
        super.init()
    }

    /// Call on every launch (foreground or background relaunch) before anything else.
    func reattach() async {
        let tasks = await session.allTasks
        let live = tasks.map { UInt64($0.taskIdentifier) }
        let reset = (try? core.reconcileSession(sessionId: Self.sessionId, liveTaskIds: live)) ?? 0
        Log.write("reattach live=\(live.count) orphans_reset=\(reset)")
    }

    /// Hand every spooled part to the system as a FILE. `presign` asks the Worker (or the
    /// kit's presign helper) for an UploadPart URL.
    func handOffPending(presign: (String, UInt32) async throws -> URL) async throws {
        for t in try core.pendingHandoffs() {
            var req = URLRequest(url: try await presign(t.uploadId, t.partNumber))
            req.httpMethod = "PUT"
            let task = session.uploadTask(with: req, fromFile: URL(fileURLWithPath: t.filePath))
            task.taskDescription = "\(t.uploadId)/\(t.partNumber)"  // survives relaunch; log it too
            // Record BEFORE resume(), so a completion can never arrive for an unknown task.
            try core.markEnqueued(sessionId: Self.sessionId, taskId: UInt64(task.taskIdentifier),
                                  uploadId: t.uploadId, partNumber: t.partNumber)
            task.resume()
        }
    }

    // MARK: URLSessionTaskDelegate

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        let http = task.response as? HTTPURLResponse
        let etag = http?.value(forHTTPHeaderField: "ETag")
        let outcome = try? core.recordTaskResult(sessionId: Self.sessionId,
                                                 taskId: UInt64(task.taskIdentifier),
                                                 httpStatus: UInt16(http?.statusCode ?? 0),
                                                 etag: etag, error: error.map { "\($0)" })
        Log.write("complete task=\(task.taskIdentifier) desc=\(task.taskDescription ?? "-") " +
                  "status=\(http?.statusCode ?? 0) etag=\(etag ?? "-") err=\(error.map { "\($0)" } ?? "-") " +
                  "outcome=\(String(describing: outcome)) appState=\(Log.appState())")
    }

    func urlSessionDidFinishEvents(forBackgroundURLSession session: URLSession) {
        Log.write("didFinishEvents")
        DispatchQueue.main.async {
            self.backgroundCompletionHandler?()
            self.backgroundCompletionHandler = nil
        }
    }
}

// AppDelegate hook (UIKit life cycle; with SwiftUI use @UIApplicationDelegateAdaptor):
//
// func application(_ application: UIApplication,
//                  handleEventsForBackgroundURLSession identifier: String,
//                  completionHandler: @escaping () -> Void) {
//     Log.write("relaunched for background session \(identifier)")
//     BackgroundUploader.shared.backgroundCompletionHandler = completionHandler
//     _ = BackgroundUploader.shared.session   // recreate the session with the same identifier
// }

/// Append-only text log in Application Support; export it with the Files app or Xcode.
enum Log {
    static let url = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("b4s2-log.txt")
    static func write(_ s: String) {
        let line = "\(ISO8601DateFormatter().string(from: Date())) \(s)\n"
        if let h = try? FileHandle(forWritingTo: url) {
            h.seekToEndOfFile(); h.write(line.data(using: .utf8)!); try? h.close()
        } else {
            try? line.data(using: .utf8)!.write(to: url)
        }
    }
    static func appState() -> String {
        // Called off the main thread; good enough for a log line.
        var s = "?"
        DispatchQueue.main.sync {
            switch UIApplication.shared.applicationState {
            case .active: s = "active"
            case .inactive: s = "inactive"
            case .background: s = "background"
            @unknown default: s = "unknown"
            }
        }
        return s
    }
}
