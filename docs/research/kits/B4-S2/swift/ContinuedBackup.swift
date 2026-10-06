// Kit B4-S2 sketch. NOT COMPILED (no Apple SDK in the research container).
// "Back up now" as a BGContinuedProcessingTask (iOS 26+), following Apple's article
// "Performing long-running tasks on iOS and iPadOS" (retrieved 2026-09-29).
// Info.plist: add the identifier to BGTaskSchedulerPermittedIdentifiers.
// Submit only from the foreground, in response to a tap.

import BackgroundTasks
import Foundation

enum ContinuedBackup {
    static let id = "org.example.reliquary.b4s2.backupnow"   // must start with your bundle ID

    /// Call once at launch (before the first submit).
    static func register(core: Core, sources: @escaping () -> [(String, PlaintextSource)]) {
        BGTaskScheduler.shared.register(forTaskWithIdentifier: id, using: nil) { task in
            guard let task = task as? BGContinuedProcessingTask else { return }
            let cancel = CancelToken()
            task.expirationHandler = {
                cancel.cancel()                       // the core stops within one 64 KiB chunk
                Log.write("continued task expired")
            }
            let work = sources()
            task.progress.totalUnitCount = Int64(work.count) * 1000
            var ok = true
            for (i, (uploadId, src)) in work.enumerated() {
                let sink = ProgressForwarder { bytesRead, _ in
                    // report often: DTS says ~30 s without progress marks the task stalled (forum 805554)
                    task.progress.completedUnitCount = Int64(i) * 1000 + Int64(min(999, bytesRead / (1 << 20)))
                }
                do {
                    let rep = try core.produceParts(uploadId: uploadId, source: src, cancel: cancel, progress: sink)
                    Log.write("continued: produced \(rep.tickets.count) parts, cancelled=\(rep.cancelled)")
                    if rep.cancelled { ok = false; break }
                } catch {
                    Log.write("continued: error \(error)"); ok = false; break
                }
                // hand off the new parts now; the background session keeps them going after this task ends
                Task { try? await BackgroundUploader.shared.handOffPending(presign: Presign.url) }
            }
            task.setTaskCompleted(success: ok)
        }
    }

    static func submit(files: Int) {
        let req = BGContinuedProcessingTaskRequest(identifier: id, title: "Backing up",
                                                   subtitle: "\(files) items")
        req.strategy = .queue   // also run once with .fail and record the difference
        do { try BGTaskScheduler.shared.submit(req) } catch { Log.write("submit failed \(error)") }
    }
}

final class ProgressForwarder: ProgressSink, @unchecked Sendable {
    let f: (UInt64, UInt32) -> Void
    init(_ f: @escaping (UInt64, UInt32) -> Void) { self.f = f }
    func onProgress(sourceBytesRead: UInt64, partsReady: UInt32) { f(sourceBytesRead, partsReady) }
}

// Presign.url(uploadId, partNumber) -> URL: calls the kit's presign helper on the LAN
// (presign_parts.py serve) or the sandbox Worker. Not included here.
