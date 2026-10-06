// Kit B4-S2 sketch. NOT COMPILED (no Apple SDK in the research container).
// Implements the B4-S1 core's forward-only `PlaintextSource` over PhotoKit.
//
// Two variants, both measured by the kit (steps B1/B8):
//  1. RequestDataSource: PHAssetResourceManager.requestData pushes chunks; a bounded queue turns
//     the push into the pull the core expects. No plaintext copy on disk. Open question the kit
//     answers: is it safe to block PhotoKit's dataReceivedHandler for back-pressure?
//  2. FileCopySource: PHAssetResourceManager.writeData(for:toFile:) first, then read the file.
//     Costs plaintext disk space (BUD-TMP) but gives random access.
// Both set isNetworkAccessAllowed so iCloud "Optimize iPhone Storage" originals are downloaded;
// with the default (false) Apple documents an error for resources that are not on the device.

import Foundation
import Photos

final class RequestDataSource: PlaintextSource, @unchecked Sendable {
    private let lock = NSCondition()
    private var queue: [Data] = []
    private var queuedBytes = 0
    private var finished = false
    private var failure: Error?
    private let maxQueued = 4 * 1024 * 1024
    private var current = Data()

    init(resource: PHAssetResource) {
        let opts = PHAssetResourceRequestOptions()
        opts.isNetworkAccessAllowed = true
        opts.progressHandler = { p in Log.write("icloud download progress \(p)") }
        PHAssetResourceManager.default().requestData(for: resource, options: opts, dataReceivedHandler: { [weak self] d in
            guard let self else { return }
            self.lock.lock()
            while self.queuedBytes > self.maxQueued { self.lock.wait() }   // back-pressure (kit question)
            self.queue.append(d); self.queuedBytes += d.count
            self.lock.signal(); self.lock.unlock()
        }, completionHandler: { [weak self] err in
            guard let self else { return }
            self.lock.lock(); self.finished = true; self.failure = err
            self.lock.broadcast(); self.lock.unlock()
        })
    }

    func read(maxLen: UInt32) throws -> Data {
        lock.lock(); defer { lock.unlock() }
        while current.isEmpty {
            if !queue.isEmpty {
                current = queue.removeFirst(); queuedBytes -= current.count; lock.broadcast()
            } else if finished {
                if let failure { throw CoreError.Source(msg: "\(failure)") }
                return Data()
            } else {
                lock.wait()
            }
        }
        let n = min(Int(maxLen), current.count)
        let out = current.prefix(n)
        current = current.dropFirst(n)
        return Data(out)
    }
}

final class FileCopySource: PlaintextSource, @unchecked Sendable {
    private let fh: FileHandle
    let tempURL: URL

    /// Blocks until PhotoKit has written the resource to a temp file.
    init(resource: PHAssetResource, tempDir: URL) throws {
        tempURL = tempDir.appendingPathComponent(UUID().uuidString)
        let opts = PHAssetResourceRequestOptions()
        opts.isNetworkAccessAllowed = true
        let done = DispatchSemaphore(value: 0)
        var err: Error?
        PHAssetResourceManager.default().writeData(for: resource, toFile: tempURL, options: opts) { e in
            err = e; done.signal()
        }
        done.wait()
        if let err { throw CoreError.Source(msg: "\(err)") }
        fh = try FileHandle(forReadingFrom: tempURL)
    }
    deinit { try? fh.close(); try? FileManager.default.removeItem(at: tempURL) }

    func read(maxLen: UInt32) throws -> Data { try fh.read(upToCount: Int(maxLen)) ?? Data() }
}

/// Source locator for one resource of one asset (ADR-0001: identifier + modification date).
func locator(for asset: PHAsset, resource: PHAssetResource) -> SourceLocator {
    let role: String
    switch resource.type {
    case .photo: role = "photo"
    case .video: role = "video"
    case .pairedVideo: role = "pairedVideo"
    case .fullSizePhoto: role = "fullSizePhoto"
    case .fullSizeVideo: role = "fullSizeVideo"
    case .alternatePhoto: role = "alternatePhoto"
    case .adjustmentData: role = "adjustmentData"
    default: role = "other-\(resource.type.rawValue)"
    }
    let version = asset.modificationDate.map { ISO8601DateFormatter().string(from: $0) } ?? "none"
    return SourceLocator(kind: .photoKitResource, localIdentifier: asset.localIdentifier,
                         cloudIdentifier: nil,  // fill from PHPhotoLibrary.cloudIdentifierMappings(forLocalIdentifiers:)
                         resourceRole: role, contentVersion: version, rawPath: nil)
}
