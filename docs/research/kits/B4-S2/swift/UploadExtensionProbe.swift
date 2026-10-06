// Kit B4-S2 sketch. NOT COMPILED (no Apple SDK in the research container).
// Probe for the PhotoKit Background Resource Upload extension, iOS 27 async protocol, following
// Apple's article "Uploading asset resources in the background" (retrieved 2026-09-29).
// On iOS 26.1-26.x use PHBackgroundResourceUploadExtension (process()/notifyTermination()) instead.
//
// Extension target Info.plist (from Apple's article):
//   EXAppExtensionAttributes > EXExtensionPointIdentifier = com.apple.photos.background-upload
//   BackgroundUploadURLBase (String, top level) = the probe server base URL, e.g. http://192.168.1.20:8080
// Host app: request .readWrite photo access, then PHPhotoLibrary.shared().setUploadJobExtensionEnabled(true).
//
// Only LAB assets on a TEST Apple Account: this extension uploads the raw resource bytes.

import Foundation
import Photos
import ExtensionFoundation
import Synchronization

@main
final class UploadExtensionProbe: PHBackgroundResourceUploadJobExtension {
    private let isCancelled = Atomic<Bool>(false)
    required init() {}

    func processJobs() async -> PHBackgroundResourceUploadProcessingResult {
        let started = Date()
        let lib = PHPhotoLibrary.shared()
        ProbeLog.write("processJobs start jobLimit=\(PHAssetResourceUploadJob.jobLimit)")   // kit A4
        do {
            // 1. acknowledge finished jobs, logging what the server returned
            let done = PHAssetResourceUploadJob.fetchJobs(action: .acknowledge, options: nil)
            for i in 0..<done.count {
                let job = done.object(at: i)
                ProbeLog.write("ack state=\(job.state.rawValue) type=\(job.type.rawValue) " +
                               "headers=\(job.responseHeaderFields ?? [:]) error=\(String(describing: job.error))")
                try await lib.performChanges {
                    PHAssetResourceUploadJobChangeRequest(for: job)?.acknowledge()
                }
            }
            // 2. create jobs for LAB assets listed by the host app in the app group (kit step A2)
            for (resource, url, method) in ProbeConfig.pendingJobs() {
                if isCancelled.load(ordering: .acquiring) { break }
                var req = URLRequest(url: url)
                req.httpMethod = method   // "PUT" for an R2 presigned URL (R2 presigns GET/PUT/HEAD/DELETE only)
                try await lib.performChanges {
                    let r = PHAssetResourceUploadJobChangeRequest.creationRequestForJob(destination: req, resource: resource)
                    ProbeLog.write("created job \(r.placeholderForCreatedAssetResourceUploadJob?.localIdentifier ?? "?") " +
                                   "resourceType=\(resource.type.rawValue) \(method) \(url.host ?? "")")
                }
            }
            // 3. kit step A8: can the extension itself read + encrypt + upload? Time it.
            if ProbeConfig.tryOwnPipeline {
                let t0 = Date()
                let n = await ProbeConfig.runOwnPipelineOnce(cancel: { self.isCancelled.load(ordering: .acquiring) })
                ProbeLog.write("own pipeline bytes=\(n) seconds=\(Date().timeIntervalSince(t0))")
            }
            ProbeLog.write("processJobs end after \(Date().timeIntervalSince(started)) s")
            return .processing
        } catch PHPhotosError.limitExceeded {
            ProbeLog.write("limitExceeded")
            return .processing
        } catch {
            ProbeLog.write("error \(error)")
            return .failure
        }
    }

    func willTerminate() async {
        isCancelled.store(true, ordering: .releasing)
        ProbeLog.write("willTerminate")   // kit A8: time between start and this line = runtime limit
    }
}

// ProbeConfig and ProbeLog: small helpers you write in Xcode that read/write the shared
// app-group container (a JSON list of LAB asset local identifiers + destination URLs, and an
// append-only log file). They are left out here because they need your app-group identifier.
