// THROWAWAY SPIKE B4-S1: an emulated iOS shell, run on Linux.
//
// It drives the Rust core through the UniFFI-generated Swift bindings the way an
// iOS app would, but the iOS parts are emulated:
//   - PhotoKit forward-only resource stream -> FileForwardSource (FileHandle, read forward only)
//   - background URLSession (nsurlsessiond)  -> "handoff" files consumed by mock/nsurlsessiond_mock.py
//   - delegate events after relaunch          -> "event" files written by the mock daemon
//   - URLSession.getAllTasks()                -> the handoff files the daemon has not taken yet
// Each run of this binary is one "wake" (launch or background relaunch).

import Foundation

final class FileForwardSource: PlaintextSource, @unchecked Sendable {
    private let fh: FileHandle
    init(path: String) throws { fh = try FileHandle(forReadingFrom: URL(fileURLWithPath: path)) }
    func read(maxLen: UInt32) throws -> Data {
        return try fh.read(upToCount: Int(maxLen)) ?? Data()
    }
}

final class CancelOnProgress: ProgressSink, @unchecked Sendable {
    let cancelAfter: UInt64
    let token: CancelToken
    var calls: UInt64 = 0
    var cancelledAt: DispatchTime? = nil
    init(cancelAfter: UInt64, token: CancelToken) { self.cancelAfter = cancelAfter; self.token = token }
    func onProgress(sourceBytesRead: UInt64, partsReady: UInt32) {
        calls += 1
        if cancelAfter > 0 && sourceBytesRead >= cancelAfter && cancelledAt == nil {
            cancelledAt = DispatchTime.now()
            token.cancel() // what BGTask.expirationHandler / willTerminate() would do
        }
    }
}

func arg(_ name: String, _ def: String) -> String {
    let a = CommandLine.arguments
    if let i = a.firstIndex(of: "--" + name), i + 1 < a.count { return a[i + 1] }
    return def
}

let state = arg("state", "./state")
let src = arg("src", "")
let budget = UInt64(arg("budget", "12582912"))!
let cpp = UInt32(arg("cpp", "80"))!
let session = arg("session", "com.example.reliquary.bg")
let port = arg("port", "18555")
let ttl = Int(arg("ttl", "3600"))!
let cancelAfter = UInt64(arg("cancel-after", "0"))!
let assetId = arg("asset-id", "SYN-ASSET-0001/L0/001")
let fm = FileManager.default
let handoff = state + "/handoff", events = state + "/events"
for d in [state, handoff, events] { try! fm.createDirectory(atPath: d, withIntermediateDirectories: true) }

var out: [String: Any] = [:]
out["core_version"] = await coreVersionAsync()

do {
    let core = try Core.open(dbPath: state + "/core.sqlite", spoolDir: state + "/spool",
                             spoolBudgetBytes: budget, chunksPerPart: cpp)

    // 1. Relaunch path: apply delivered task results (application(_:handleEventsForBackgroundURLSession:)).
    var outcomes: [String: Int] = [:]
    for f in try fm.contentsOfDirectory(atPath: events).sorted() where f.hasSuffix(".json") {
        let p = events + "/" + f
        let ev = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: p))) as! [String: Any]
        let o = try core.recordTaskResult(sessionId: ev["session"] as! String,
                                          taskId: UInt64(ev["task"] as! Int),
                                          httpStatus: UInt16(ev["status"] as! Int),
                                          etag: ev["etag"] as? String, error: ev["error"] as? String)
        let k: String
        switch o {
        case .recorded: k = "recorded"
        case .duplicate: k = "duplicate"
        case .unknownTask: k = "unknown_task"
        case .failed: k = "failed"
        }
        outcomes[k, default: 0] += 1
        try fm.removeItem(atPath: p) // only after the core has recorded it
    }
    out["event_outcomes"] = outcomes

    // 2. getAllTasks(): tasks the transfer service still holds.
    var live: [UInt64] = []
    var maxTask: UInt64 = 0
    for f in try fm.contentsOfDirectory(atPath: handoff) where f.hasSuffix(".json") {
        let t = UInt64(f.split(separator: "-").last!.split(separator: ".").first!)!
        live.append(t)
    }
    if let s = try? String(contentsOfFile: state + "/next_task_id", encoding: .utf8) { maxTask = UInt64(s.trimmingCharacters(in: .whitespacesAndNewlines))! }
    out["orphans_reset"] = try core.reconcileSession(sessionId: session, liveTaskIds: live)

    // 3. Plan or find the upload for this asset resource.
    let size = (try fm.attributesOfItem(atPath: src)[.size] as! NSNumber).uint64Value
    let loc = SourceLocator(kind: .photoKitResource, localIdentifier: assetId, cloudIdentifier: nil,
                            resourceRole: "photo", contentVersion: "2026-09-29T00:00:00Z", rawPath: nil)
    let uploadId = try core.findUpload(locator: loc) ?? core.planUpload(locator: loc, plaintextSize: size)
    out["upload_id"] = uploadId

    // 4. One short, cancellable work unit.
    let token = CancelToken()
    let prog = CancelOnProgress(cancelAfter: cancelAfter, token: token)
    let rep = try core.produceParts(uploadId: uploadId, source: try FileForwardSource(path: src),
                                    cancel: token, progress: prog)
    if let c = prog.cancelledAt {
        out["cancel_latency_us"] = (DispatchTime.now().uptimeNanoseconds - c.uptimeNanoseconds) / 1000
    }
    out["produced_parts"] = rep.tickets.map { $0.partNumber }
    out["source_bytes_read"] = rep.sourceBytesRead
    out["cancelled"] = rep.cancelled
    out["spool_bytes_after"] = rep.spoolBytesAfter
    out["produce_ms"] = rep.elapsedMs
    out["progress_callbacks"] = prog.calls

    // 5. Hand every spooled part to the transfer service as a FILE (never Data/stream).
    //    Order: create task -> core.markEnqueued -> resume(), emulated by .pending -> .json rename.
    let exp = Int(Date().timeIntervalSince1970) + ttl
    var handed: [UInt32] = []
    for t in try core.pendingHandoffs() {
        maxTask += 1
        let base = "\(handoff)/\(session)-\(maxTask)"
        let job: [String: Any] = ["session": session, "task": maxTask, "file": t.filePath,
                                  "url": "http://127.0.0.1:\(port)/\(t.uploadId)/\(t.partNumber)?exp=\(exp)"]
        try JSONSerialization.data(withJSONObject: job).write(to: URL(fileURLWithPath: base + ".pending"))
        try core.markEnqueued(sessionId: session, taskId: maxTask, uploadId: t.uploadId, partNumber: t.partNumber)
        try fm.moveItem(atPath: base + ".pending", toPath: base + ".json") // resume()
        handed.append(t.partNumber)
    }
    try String(maxTask).write(toFile: state + "/next_task_id", atomically: true, encoding: .utf8)
    out["handed_off"] = handed

    let st = try core.uploadStatus(uploadId: uploadId)
    out["status"] = ["n_parts": st.nParts, "uploaded": st.uploaded, "enqueued": st.enqueued,
                     "spooled": st.spooled, "missing": st.missing, "not_started": st.notStarted,
                     "complete": st.complete]
    out["ok"] = true
} catch {
    out["ok"] = false
    out["error"] = "\(error)"
}
print(String(data: try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys]), encoding: .utf8)!)
