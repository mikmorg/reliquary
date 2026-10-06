// B7-S1 probe app: records what macOS lets this exact build do, so that v1 and v2
// of each signing arm can be compared across a self-update.
//
// NOT COMPILED IN THE RESEARCH CONTAINER (no Apple SDK there). build.sh compiles it
// on the test Mac with the Xcode Command Line Tools. If it fails to compile, fix the
// smallest thing possible and note the fix in results.md.
//
// Modes (first argument):
//   (none)               run all checks as the app, write JSON, show a summary, quit
//   --helper             run all checks headless (used by the LaunchAgent), write JSON, exit
//   --register-helper    SMAppService.agent(...).register(), record the status, quit
//   --unregister-helper  SMAppService.agent(...).unregister(), record the status, quit
//
// Data handling: only counts, status codes and hashes of SYNTHETIC keychain secrets are
// written. No file names, no photo content, no personal data. Results go to
// ~/Library/Application Support/org.reliquary.b7s1/results/ (not a TCC-protected folder).

import AppKit
import CryptoKit
import Foundation
import Photos
import Security
import ServiceManagement

let kBundleID = "org.reliquary.b7s1probe"
let kHelperPlist = "org.reliquary.b7s1probe.helper.plist"
let kFileKeychainService = "org.reliquary.b7s1.file-keychain"
let kDPKeychainService = "org.reliquary.b7s1.dp-keychain"
let kAccount = "b7s1-test"
// build.sh replaces this marker so that v1 and v2 differ in code as well as in Info.plist.
let kBuildMarker = "B7S1_BUILD_MARKER"

let supportDir = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/org.reliquary.b7s1")
let resultsDir = supportDir.appendingPathComponent("results")

func nowISO() -> String {
    let f = ISO8601DateFormatter()
    f.formatOptions = [.withInternetDateTime]
    return f.string(from: Date())
}

func hexString(_ data: Data) -> String {
    data.map { String(format: "%02x", $0) }.joined()
}

func sha256Prefix(_ data: Data) -> String {
    String(hexString(Data(SHA256.hash(data: data))).prefix(16))
}

func errorText(_ status: OSStatus) -> String {
    (SecCopyErrorMessageString(status, nil) as String?) ?? "?"
}

// MARK: - Who am I (the identity macOS computes for this running build)

func selfIdentity() -> [String: Any] {
    var out: [String: Any] = [:]
    var code: SecCode?
    let st = SecCodeCopySelf(SecCSFlags(), &code)
    out["SecCodeCopySelf_status"] = Int(st)
    guard st == errSecSuccess, let running = code else { return out }

    var staticCode: SecStaticCode?
    let st2 = SecCodeCopyStaticCode(running, SecCSFlags(), &staticCode)
    out["SecCodeCopyStaticCode_status"] = Int(st2)
    guard st2 == errSecSuccess, let sc = staticCode else { return out }

    // The designated requirement (DR) as macOS computes it. For ad-hoc code this is an
    // implicit cdhash requirement; for a self-signed identity it should be
    // identifier + certificate hash (research note C3, C4). This is the value under test.
    var req: SecRequirement?
    let st3 = SecCodeCopyDesignatedRequirement(sc, SecCSFlags(), &req)
    out["designated_requirement_status"] = Int(st3)
    if st3 == errSecSuccess, let r = req {
        var text: CFString?
        if SecRequirementCopyString(r, SecCSFlags(), &text) == errSecSuccess, let t = text {
            out["designated_requirement"] = t as String
        }
    }

    var info: CFDictionary?
    let st4 = SecCodeCopySigningInformation(sc, SecCSFlags(rawValue: UInt32(kSecCSSigningInformation)), &info)
    out["signing_information_status"] = Int(st4)
    if st4 == errSecSuccess, let d = info as? [String: Any] {
        if let u = d[kSecCodeInfoUnique as String] as? Data { out["cdhash"] = hexString(u) }
        if let t = d[kSecCodeInfoTeamIdentifier as String] as? String { out["team_id"] = t }
        if let i = d[kSecCodeInfoIdentifier as String] as? String { out["signing_identifier"] = i }
        if let certs = d[kSecCodeInfoCertificates as String] as? [SecCertificate] {
            out["certificate_count"] = certs.count
            out["certificate_subjects"] = certs.map { (SecCertificateCopySubjectSummary($0) as String?) ?? "?" }
            out["certificate_sha1"] = certs.map { cert -> String in
                let der = SecCertificateCopyData(cert) as Data
                return hexString(Data(Insecure.SHA1.hash(data: der)))
            }
        }
    }
    return out
}

// MARK: - Photos

func photosStatusName(_ s: PHAuthorizationStatus) -> String {
    switch s {
    case .notDetermined: return "notDetermined"
    case .restricted: return "restricted"
    case .denied: return "denied"
    case .authorized: return "authorized"
    case .limited: return "limited"
    @unknown default: return "unknown(\(s.rawValue))"
    }
}

func photosCheck() -> [String: Any] {
    var out: [String: Any] = [:]
    let before = PHPhotoLibrary.authorizationStatus(for: .readWrite)
    out["status_before"] = photosStatusName(before)
    var status = before
    if before == .notDetermined {
        let sem = DispatchSemaphore(value: 0)
        let t0 = Date()
        PHPhotoLibrary.requestAuthorization(for: .readWrite) { s in
            status = s
            sem.signal()
        }
        sem.wait()
        out["request_seconds"] = Date().timeIntervalSince(t0)
    }
    out["status_after"] = photosStatusName(status)
    if status == .authorized || status == .limited {
        // Count only. Use a test macOS account with an empty or LAB-only library.
        out["asset_count"] = PHAsset.fetchAssets(with: nil).count
    }
    return out
}

// MARK: - Files and Folders, removable volume, Full Disk Access

func listCheck(_ path: String) -> [String: Any] {
    var out: [String: Any] = ["path_kind": path.hasPrefix("/Volumes/") ? "removable-volume" : "home-subfolder"]
    let t0 = Date()
    do {
        let items = try FileManager.default.contentsOfDirectory(atPath: path)
        out["ok"] = true
        out["entry_count"] = items.count
    } catch let e as NSError {
        out["ok"] = false
        out["error_domain"] = e.domain
        out["error_code"] = e.code
        if let u = e.userInfo[NSUnderlyingErrorKey] as? NSError {
            out["underlying_domain"] = u.domain
            out["underlying_code"] = u.code
        }
    }
    out["seconds"] = Date().timeIntervalSince(t0)
    return out
}

// Heuristic only: reading the per-user TCC database needs Full Disk Access.
// EPERM (1) means "no FDA"; success means FDA is in effect for this build.
func fullDiskAccessCheck() -> [String: Any] {
    let path = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/com.apple.TCC/TCC.db").path
    let fd = open(path, O_RDONLY)
    if fd >= 0 {
        close(fd)
        return ["ok": true, "method": "open(user TCC.db)"]
    }
    return ["ok": false, "errno": Int(errno), "method": "open(user TCC.db)"]
}

func removableVolumePath() -> String? {
    let f = supportDir.appendingPathComponent("volume-path.txt")
    guard let s = try? String(contentsOf: f, encoding: .utf8) else { return nil }
    let p = s.trimmingCharacters(in: .whitespacesAndNewlines)
    return p.isEmpty ? nil : p
}

// MARK: - Keychain

func keychainCheck(service: String, dataProtection: Bool) -> [String: Any] {
    var out: [String: Any] = ["data_protection_keychain": dataProtection]
    var q: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: service,
        kSecAttrAccount as String: kAccount,
        kSecReturnData as String: true,
        kSecMatchLimit as String: kSecMatchLimitOne,
    ]
    if dataProtection { q[kSecUseDataProtectionKeychain as String] = true }
    var result: CFTypeRef?
    let t0 = Date()
    let st = SecItemCopyMatching(q as CFDictionary, &result)
    out["read_seconds"] = Date().timeIntervalSince(t0)  // a long time usually means a prompt was shown
    out["read_status"] = Int(st)
    out["read_status_text"] = errorText(st)
    if st == errSecSuccess, let data = result as? Data {
        out["found_existing_item"] = true
        out["read_value_sha256_prefix"] = sha256Prefix(data)
    } else if st == errSecItemNotFound {
        out["found_existing_item"] = false
        // Synthetic secret (SYN). Its hash prefix lets v2 prove it read v1's item.
        let secret = Data("synthetic-\(UUID().uuidString)".utf8)
        var add: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: kAccount,
            kSecAttrLabel as String: "Reliquary B7-S1 test item",
            kSecValueData as String: secret,
        ]
        if dataProtection { add[kSecUseDataProtectionKeychain as String] = true }
        let a = SecItemAdd(add as CFDictionary, nil)
        out["add_status"] = Int(a)
        out["add_status_text"] = errorText(a)
        if a == errSecSuccess { out["written_value_sha256_prefix"] = sha256Prefix(secret) }
    }
    return out
}

// MARK: - LaunchAgent helper (SMAppService, macOS 13+)

func smStatusName(_ s: SMAppService.Status) -> String {
    switch s {
    case .notRegistered: return "notRegistered"
    case .enabled: return "enabled"
    case .requiresApproval: return "requiresApproval"
    case .notFound: return "notFound"
    @unknown default: return "unknown(\(s.rawValue))"
    }
}

func helperAction(_ action: String) -> [String: Any] {
    let svc = SMAppService.agent(plistName: kHelperPlist)
    var out: [String: Any] = ["status_before": smStatusName(svc.status)]
    do {
        if action == "register" { try svc.register() } else { try svc.unregister() }
        out["ok"] = true
    } catch let e as NSError {
        out["ok"] = false
        out["error_domain"] = e.domain
        out["error_code"] = e.code
        out["error_text"] = e.localizedDescription
    }
    out["status_after"] = smStatusName(svc.status)
    return out
}

// MARK: - Run and record

func runAllChecks(mode: String) -> [String: Any] {
    let home = FileManager.default.homeDirectoryForCurrentUser
    var r: [String: Any] = [
        "kit": "B7-S1",
        "mode": mode,
        "time": nowISO(),
        "version": (Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String) ?? "?",
        "build_marker": kBuildMarker,
        "bundle_path_kind": Bundle.main.bundlePath.hasPrefix(home.path) ? "under-home" : "outside-home",
        "os": ProcessInfo.processInfo.operatingSystemVersionString,
        "pid": Int(ProcessInfo.processInfo.processIdentifier),
        "ppid": Int(getppid()),
    ]
    r["self"] = selfIdentity()
    r["photos"] = photosCheck()
    r["documents"] = listCheck(home.appendingPathComponent("Documents").path)
    r["desktop"] = listCheck(home.appendingPathComponent("Desktop").path)
    r["downloads"] = listCheck(home.appendingPathComponent("Downloads").path)
    if let v = removableVolumePath() { r["removable_volume"] = listCheck(v) } else { r["removable_volume"] = ["skipped": "no volume-path.txt"] }
    r["full_disk_access"] = fullDiskAccessCheck()
    r["keychain_file_based"] = keychainCheck(service: kFileKeychainService, dataProtection: false)
    r["keychain_data_protection"] = keychainCheck(service: kDPKeychainService, dataProtection: true)
    r["helper_status"] = smStatusName(SMAppService.agent(plistName: kHelperPlist).status)
    return r
}

@discardableResult
func writeResults(_ r: [String: Any]) -> String {
    try? FileManager.default.createDirectory(at: resultsDir, withIntermediateDirectories: true)
    let stamp = nowISO().replacingOccurrences(of: ":", with: "-")
    let name = "\(r["version"] ?? "x")-\(r["mode"] ?? "x")-\(stamp).json"
    let url = resultsDir.appendingPathComponent(name)
    if let data = try? JSONSerialization.data(withJSONObject: r, options: [.prettyPrinted, .sortedKeys]) {
        try? data.write(to: url)
    }
    return url.path
}

func summary(_ r: [String: Any]) -> String {
    func ok(_ key: String) -> String {
        guard let d = r[key] as? [String: Any] else { return "?" }
        if let b = d["ok"] as? Bool { return b ? "OK" : "DENIED" }
        return "-"
    }
    let photos = (r["photos"] as? [String: Any])?["status_after"] as? String ?? "?"
    let kf = (r["keychain_file_based"] as? [String: Any])?["read_status"] as? Int
    let kd = (r["keychain_data_protection"] as? [String: Any])?["read_status"] as? Int
    let dr = (r["self"] as? [String: Any])?["designated_requirement"] as? String ?? "?"
    return """
    Version \(r["version"] ?? "?") (\(r["mode"] ?? "?"))
    Photos: \(photos)
    Documents: \(ok("documents"))  Desktop: \(ok("desktop"))  Downloads: \(ok("downloads"))
    Removable volume: \(ok("removable_volume"))  Full Disk Access: \(ok("full_disk_access"))
    Keychain (file-based) read status: \(kf.map(String.init) ?? "?")
    Keychain (data protection) read status: \(kd.map(String.init) ?? "?")
    Helper: \(r["helper_status"] ?? "?")
    DR: \(dr)
    """
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    let mode: String
    init(mode: String) { self.mode = mode }

    func applicationDidFinishLaunching(_ notification: Notification) {
        DispatchQueue.global(qos: .userInitiated).async {
            var r: [String: Any]
            switch self.mode {
            case "register-helper", "unregister-helper":
                r = ["kit": "B7-S1", "mode": self.mode, "time": nowISO(),
                     "version": (Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String) ?? "?"]
                r["helper"] = helperAction(self.mode == "register-helper" ? "register" : "unregister")
                r["self"] = selfIdentity()
            default:
                r = runAllChecks(mode: "app")
            }
            let path = writeResults(r)
            DispatchQueue.main.async {
                NSApp.activate(ignoringOtherApps: true)
                let alert = NSAlert()
                alert.messageText = "Reliquary B7-S1 probe"
                alert.informativeText = summary(r) + "\n\nSaved: \(path)"
                alert.addButton(withTitle: "Quit")
                alert.runModal()
                NSApp.terminate(nil)
            }
        }
    }
}

let args = CommandLine.arguments
if args.contains("--helper") {
    // LaunchAgent mode: no UI of our own. Any prompt that appears is macOS's.
    writeResults(runAllChecks(mode: "helper"))
    exit(0)
}
let mode: String
if args.contains("--register-helper") {
    mode = "register-helper"
} else if args.contains("--unregister-helper") {
    mode = "unregister-helper"
} else {
    mode = "app"
}
let app = NSApplication.shared
let delegate = AppDelegate(mode: mode)
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
