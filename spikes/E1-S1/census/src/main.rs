//! E1-S1 census spike (THROWAWAY). Counts files by category, extension group and log2 size bin,
//! without exporting any filename, path, hash, GPS or exact per-file size (H3 §3–§4, §7.6).
//!
//! Design points under test (docs/research/e1-family-research-census.md §3):
//! - std-based walker (jwalk is deprecated; dua-core hides placeholder bits);
//! - placeholder check (Windows attribute bits, macOS SF_DATALESS) BEFORE any read, from the
//!   directory-entry metadata only; placeholders are never opened;
//! - classification by extension first; magic-byte sniffing only for local files with no or
//!   unknown extension (`--no-sniff` disables it);
//! - optional EXIF/track parsing (`--exif`) for capture month and camera model;
//! - show-before-save (H3 R6): everything that would be saved is printed first, then the person
//!   is asked; `--yes` skips the question for rehearsals on synthetic data only.

use std::collections::BTreeMap;
use std::fs::{self, DirEntry, Metadata};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::time::{Instant, SystemTime, UNIX_EPOCH};

const VERSION: &str = "e1-s1-spike-0.1";
const SUPPRESS_BELOW: u64 = 5; // H3 §4: cells below 5 are shown as "<5"
const MONTHS_BACK: i64 = 24;

// ---------------------------------------------------------------- placeholders (per platform)

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
enum State {
    Local,
    CloudOnly,
}

#[cfg(windows)]
fn placeholder_state(md: &Metadata) -> State {
    use std::os::windows::fs::MetadataExt;
    const FILE_ATTRIBUTE_OFFLINE: u32 = 0x0000_1000;
    const FILE_ATTRIBUTE_RECALL_ON_OPEN: u32 = 0x0004_0000;
    const FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS: u32 = 0x0040_0000;
    let a = md.file_attributes();
    if a & (FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS) != 0 {
        State::CloudOnly
    } else {
        State::Local
    }
}

#[cfg(target_vendor = "apple")]
fn placeholder_state(md: &Metadata) -> State {
    use std::os::darwin::fs::MetadataExt;
    const SF_DATALESS: u32 = 0x4000_0000; // xnu bsd/sys/stat.h
    if md.st_flags() & SF_DATALESS != 0 {
        State::CloudOnly
    } else {
        State::Local
    }
}

#[cfg(all(not(any(windows, target_vendor = "apple")), not(feature = "emulate-placeholders")))]
fn placeholder_state(_md: &Metadata) -> State {
    State::Local // Linux: no cloud-placeholder convention to detect
}

/// EMULATION ONLY (rehearsal on Linux): a regular file with the sticky bit set stands in for a
/// cloud placeholder. Like the real checks, it uses only the enumeration metadata (lstat).
#[cfg(all(not(any(windows, target_vendor = "apple")), feature = "emulate-placeholders"))]
fn placeholder_state(md: &Metadata) -> State {
    use std::os::unix::fs::PermissionsExt;
    if md.permissions().mode() & 0o1000 != 0 { State::CloudOnly } else { State::Local }
}

#[cfg(unix)]
fn dev_of(md: &Metadata) -> Option<u64> {
    use std::os::unix::fs::MetadataExt;
    Some(md.dev())
}
#[cfg(not(unix))]
fn dev_of(_md: &Metadata) -> Option<u64> {
    None
}

// ---------------------------------------------------------------- classification

/// (category, ext_group) from a lower-case extension. Fixed vocabulary: nothing user-derived.
fn classify_ext(ext: &str) -> Option<(&'static str, &'static str)> {
    Some(match ext {
        "jpg" | "jpeg" | "jpe" | "jfif" => ("photo", "jpeg"),
        "heic" | "heif" | "hif" => ("photo", "heif"),
        "avif" => ("photo", "avif"),
        "png" => ("photo", "png"),
        "gif" => ("photo", "gif"),
        "webp" => ("photo", "webp"),
        "tif" | "tiff" => ("photo", "tiff"),
        "bmp" => ("photo", "bmp"),
        "jxl" => ("photo", "jxl"),
        "dng" => ("raw", "raw-dng"),
        "cr2" | "cr3" | "crw" => ("raw", "raw-canon"),
        "nef" | "nrw" => ("raw", "raw-nikon"),
        "arw" | "srf" | "sr2" => ("raw", "raw-sony"),
        "orf" => ("raw", "raw-olympus"),
        "rw2" => ("raw", "raw-panasonic"),
        "raf" => ("raw", "raw-fuji"),
        "pef" | "srw" | "x3f" | "3fr" | "iiq" | "erf" | "mrw" | "kdc" | "dcr" => ("raw", "raw-other"),
        "mov" | "qt" => ("video", "mov"),
        "mp4" | "m4v" => ("video", "mp4"),
        "3gp" | "3g2" => ("video", "3gp"),
        "mts" | "m2ts" | "tod" | "mod" => ("video", "avchd-mpegts"),
        "avi" => ("video", "avi"),
        "mkv" | "webm" => ("video", "matroska"),
        "wmv" | "asf" => ("video", "wmv"),
        "mpg" | "mpeg" | "vob" => ("video", "mpeg"),
        "dv" => ("video", "dv"),
        "m4a" | "aac" => ("audio", "aac"),
        "mp3" => ("audio", "mp3"),
        "wav" | "aif" | "aiff" => ("audio", "pcm"),
        "flac" | "alac" => ("audio", "lossless"),
        "amr" | "opus" | "ogg" | "oga" | "caf" | "wma" => ("audio", "voice-other"),
        "pdf" => ("document", "pdf"),
        "doc" | "docx" | "dot" | "dotx" | "rtf" => ("document", "word"),
        "xls" | "xlsx" | "csv" | "numbers" => ("document", "spreadsheet"),
        "ppt" | "pptx" | "key" => ("document", "slides"),
        "odt" | "ods" | "odp" => ("document", "opendocument"),
        "pages" => ("document", "pages"),
        "txt" | "md" => ("document", "text"),
        "eml" | "msg" | "mbox" | "pst" | "ost" | "emlx" => ("email", "mail"),
        "ged" | "gedcom" | "ftm" | "gramps" => ("genealogy", "gedcom-etc"),
        "zip" | "7z" | "rar" | "tar" | "gz" | "tgz" | "bz2" | "xz" => ("archive", "archive"),
        "iso" | "dmg" | "img" | "vhd" | "vhdx" | "vmdk" => ("disk-image", "disk-image"),
        "xmp" | "aae" | "thm" => ("sidecar", "sidecar"),
        "exe" | "dll" | "so" | "dylib" | "msi" | "app" | "sys" | "pyc" | "class" | "o" | "a" | "lib" => {
            ("app-or-system", "binary")
        }
        "js" | "ts" | "py" | "rs" | "c" | "h" | "java" | "go" | "json" | "xml" | "html" | "css" | "yml" | "yaml"
        | "toml" | "ini" | "log" | "db" | "sqlite" | "lock" | "tmp" | "cache" | "dat" => ("app-or-system", "data"),
        _ => return None,
    })
}

fn classify_mime(t: &infer::Type) -> (&'static str, &'static str) {
    use infer::MatcherType::*;
    match t.matcher_type() {
        Image => match t.extension() {
            "cr2" => ("raw", "sniffed-raw"),
            _ => ("photo", "sniffed-image"),
        },
        Video => ("video", "sniffed-video"),
        Audio => ("audio", "sniffed-audio"),
        Doc | Book => ("document", "sniffed-document"),
        Archive => ("archive", "sniffed-archive"),
        App => ("app-or-system", "sniffed-binary"),
        _ => ("other", "sniffed-other"),
    }
}

/// Coarse location class from path components below the root. Fixed vocabulary; the path itself
/// never leaves this function.
fn location_class(rel: &Path) -> (&'static str, bool) {
    let comps: Vec<String> = rel
        .components()
        .map(|c| c.as_os_str().to_string_lossy().to_lowercase())
        .collect();
    let dirs = if comps.is_empty() { &comps[..] } else { &comps[..comps.len() - 1] };
    // Apple Photos library package: only originals/ (Masters/ in old libraries) holds originals.
    for (i, c) in dirs.iter().enumerate() {
        if c.ends_with(".photoslibrary") {
            let inner = dirs.get(i + 1).map(|s| s.as_str()).unwrap_or("");
            return ("apple-photos-library", inner == "originals" || inner == "masters");
        }
    }
    let joined = dirs.join("/");
    let is = |pat: &str| dirs.iter().any(|c| c == pat);
    let starts = |pat: &str| dirs.iter().any(|c| c.starts_with(pat));
    if starts("onedrive") || is("icloud drive") || is("iclouddrive") || joined.contains("library/mobile documents")
        || joined.contains("library/cloudstorage") || starts("dropbox") || is("google drive") || is("my drive")
    {
        return ("cloud-sync-folder", false);
    }
    if starts("whatsapp") || is("telegram desktop") || is("telegram") || is("signal") || is("viber") {
        return ("messaging-app", false);
    }
    if is("appdata") || dirs.first().map(|c| c == "library").unwrap_or(false) || is(".cache") || is(".local")
        || is(".config") || is(".var") || is("snap") || is("node_modules") || is(".git") || is(".cargo")
        || is(".rustup") || is("$recycle.bin") || is(".trash")
    {
        return ("app-data-or-cache", false);
    }
    let first = dirs.first().map(|s| s.as_str()).unwrap_or("");
    let cls = match first {
        "pictures" | "photos" | "my pictures" | "dcim" => "pictures",
        "videos" | "movies" | "my videos" => "videos",
        "documents" | "my documents" => "documents",
        "desktop" => "desktop",
        "downloads" => "downloads",
        "music" | "my music" => "music",
        "" => "root",
        _ => "other",
    };
    (cls, false)
}

fn log2_bin(size: u64) -> String {
    if size == 0 {
        "zero".to_string()
    } else {
        (63 - size.leading_zeros()).to_string()
    }
}

// ---------------------------------------------------------------- aggregation

#[derive(Default, Clone, Copy)]
struct Cell {
    count: u64,
    bytes: u64,
}
impl Cell {
    fn add(&mut self, b: u64) {
        self.count += 1;
        self.bytes += b;
    }
}

#[derive(Default)]
struct Totals {
    files: u64,
    dirs: u64,
    symlinks_skipped: u64,
    other_fs_skipped: u64,
    unreadable_dirs: u64,
    unreadable_entries: u64,
    placeholders: u64,
    sniffed: u64,
    exif_ok: u64,
    exif_fail: u64,
    // (category, ext_group, bin) -> cell; separate maps for local and cloud-only files
    local: BTreeMap<(String, String, String), Cell>,
    cloud: BTreeMap<(String, String, String), Cell>,
    // (location_class, state, category)
    locations: BTreeMap<(String, String, String), Cell>,
    // (category, month or "earlier"/"unknown", source)
    months: BTreeMap<(String, String, String), Cell>,
    // (make, model) for media with EXIF/track metadata
    cameras: BTreeMap<(String, String), Cell>,
    // local-only, never exported: candidate folders (path -> media count)
    candidates: BTreeMap<PathBuf, u64>,
}

struct Opts {
    roots: Vec<PathBuf>,
    out: PathBuf,
    sniff: bool,
    exif: bool,
    yes: bool,
    one_fs: bool,
    list_candidates: bool,
}

fn now_month_index() -> i64 {
    let secs = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0);
    let (y, m) = civil_from_days(secs.div_euclid(86_400));
    y * 12 + (m - 1)
}

/// Howard Hinnant's days -> civil date algorithm (year, month).
fn civil_from_days(z: i64) -> (i64, i64) {
    let z = z + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (if m <= 2 { y + 1 } else { y }, m)
}

fn month_label(y: i64, m: i64, now_idx: i64) -> String {
    let idx = y * 12 + (m - 1);
    if idx > now_idx {
        "future".into()
    } else if now_idx - idx >= MONTHS_BACK {
        "earlier".into()
    } else {
        format!("{y:04}-{m:02}")
    }
}

fn mtime_month(md: &Metadata) -> Option<(i64, i64)> {
    let t = md.modified().ok()?;
    let secs = match t.duration_since(UNIX_EPOCH) {
        Ok(d) => d.as_secs() as i64,
        Err(e) => -(e.duration().as_secs() as i64),
    };
    Some(civil_from_days(secs.div_euclid(86_400)))
}

/// Capture month and (make, model) from EXIF or track metadata. Reads file data.
fn exif_info(parser: &mut nom_exif::MediaParser, path: &Path) -> Option<(Option<(i64, i64)>, Option<(String, String)>)> {
    use nom_exif::{ExifTag, MediaKind, MediaSource, TrackInfoTag};
    let ms = MediaSource::open(path).ok()?;
    let digits = |s: String| -> Option<(i64, i64)> {
        let d: String = s.chars().filter(|c| c.is_ascii_digit()).take(6).collect();
        if d.len() < 6 {
            return None;
        }
        let y: i64 = d[0..4].parse().ok()?;
        let m: i64 = d[4..6].parse().ok()?;
        if (1..=12).contains(&m) && y > 1900 { Some((y, m)) } else { None }
    };
    let clean = |s: Option<&str>| s.map(|v| v.trim().trim_matches('\0').to_string()).filter(|v| !v.is_empty());
    match ms.kind() {
        MediaKind::Image => {
            let exif: nom_exif::Exif = parser.parse_exif(ms).ok()?.into();
            let when = exif
                .get(ExifTag::DateTimeOriginal)
                .or_else(|| exif.get(ExifTag::CreateDate))
                .and_then(|v| digits(v.to_string()));
            let make = clean(exif.get(ExifTag::Make).and_then(|v| v.as_str()));
            let model = clean(exif.get(ExifTag::Model).and_then(|v| v.as_str()));
            let cam = if make.is_some() || model.is_some() {
                Some((make.unwrap_or_default(), model.unwrap_or_default()))
            } else {
                None
            };
            Some((when, cam))
        }
        MediaKind::Track => {
            let info = parser.parse_track(ms).ok()?;
            let when = info.get(TrackInfoTag::CreateDate).and_then(|v| digits(v.to_string()));
            let make = clean(info.get(TrackInfoTag::Make).and_then(|v| v.as_str()));
            let model = clean(info.get(TrackInfoTag::Model).and_then(|v| v.as_str()));
            let cam = if make.is_some() || model.is_some() {
                Some((make.unwrap_or_default(), model.unwrap_or_default()))
            } else {
                None
            };
            Some((when, cam))
        }
    }
}

fn sniff(path: &Path) -> Option<(&'static str, &'static str)> {
    let mut f = fs::File::open(path).ok()?;
    let mut buf = vec![0u8; 8192];
    let mut n = 0;
    while n < buf.len() {
        match f.read(&mut buf[n..]) {
            Ok(0) => break,
            Ok(k) => n += k,
            Err(_) => return None,
        }
    }
    infer::get(&buf[..n]).map(|t| classify_mime(&t))
}

fn visit_file(t: &mut Totals, o: &Opts, parser: &mut nom_exif::MediaParser, now_idx: i64, root: &Path, e: &DirEntry, md: &Metadata) {
    t.files += 1;
    let path = e.path();
    let size = md.len();
    let state = placeholder_state(md); // from enumeration metadata only; no open()
    let rel = path.strip_prefix(root).unwrap_or(&path);
    let (loc, in_originals) = location_class(rel);
    let ext = path.extension().map(|x| x.to_string_lossy().to_lowercase());
    let mut class = ext.as_deref().and_then(classify_ext);
    if loc == "apple-photos-library" && !in_originals {
        class = Some(("library-internal", "library-internal"));
    }
    if class.is_none() && state == State::Local && o.sniff && size > 0 {
        t.sniffed += 1;
        class = sniff(&path);
    }
    let (cat, grp) = class.unwrap_or(("other", if ext.is_some() { "other-ext" } else { "no-ext" }));
    let key = (cat.to_string(), grp.to_string(), log2_bin(size));
    match state {
        State::Local => t.local.entry(key).or_default().add(size),
        State::CloudOnly => {
            t.placeholders += 1;
            t.cloud.entry(key).or_default().add(size)
        }
    }
    let st = if state == State::Local { "local" } else { "cloud-only" };
    t.locations.entry((loc.into(), st.into(), cat.into())).or_default().add(size);

    let is_media = matches!(cat, "photo" | "raw" | "video");
    if !is_media {
        return;
    }
    if o.list_candidates && matches!(loc, "other" | "root" | "desktop" | "documents" | "downloads") {
        if let Some(parent) = path.parent() {
            *t.candidates.entry(parent.to_path_buf()).or_default() += 1;
        }
    }
    let mut when = None;
    let mut source = "mtime";
    if o.exif && state == State::Local {
        match exif_info(parser, &path) {
            Some((w, cam)) => {
                t.exif_ok += 1;
                if w.is_some() {
                    when = w;
                    source = "exif";
                }
                if let Some((mk, md_)) = cam {
                    t.cameras.entry((mk, md_)).or_default().add(size);
                }
            }
            None => t.exif_fail += 1,
        }
    }
    if when.is_none() {
        when = mtime_month(md);
        source = "mtime";
    }
    let label = when.map(|(y, m)| month_label(y, m, now_idx)).unwrap_or_else(|| "unknown".into());
    t.months.entry((cat.into(), label, source.into())).or_default().add(size);
}

fn walk(o: &Opts, t: &mut Totals) {
    let now_idx = now_month_index();
    let mut parser = nom_exif::MediaParser::new();
    for root in &o.roots {
        let root_dev = fs::symlink_metadata(root).ok().and_then(|m| dev_of(&m));
        let mut stack = vec![root.clone()];
        while let Some(dir) = stack.pop() {
            t.dirs += 1;
            let rd = match fs::read_dir(&dir) {
                Ok(rd) => rd,
                Err(_) => {
                    t.unreadable_dirs += 1;
                    continue;
                }
            };
            for ent in rd {
                let e = match ent {
                    Ok(e) => e,
                    Err(_) => {
                        t.unreadable_entries += 1;
                        continue;
                    }
                };
                let ft = match e.file_type() {
                    Ok(ft) => ft,
                    Err(_) => {
                        t.unreadable_entries += 1;
                        continue;
                    }
                };
                if ft.is_symlink() {
                    t.symlinks_skipped += 1;
                    continue;
                }
                let md = match e.metadata() {
                    Ok(m) => m,
                    Err(_) => {
                        t.unreadable_entries += 1;
                        continue;
                    }
                };
                if ft.is_dir() {
                    if o.one_fs && root_dev.is_some() && dev_of(&md) != root_dev {
                        t.other_fs_skipped += 1;
                        continue;
                    }
                    stack.push(e.path());
                } else if ft.is_file() {
                    visit_file(t, o, &mut parser, now_idx, root, &e, &md);
                }
            }
        }
    }
}

// ---------------------------------------------------------------- output (H3 §4 applied here)

fn cell_str(c: &Cell) -> (String, String) {
    if c.count < SUPPRESS_BELOW {
        ("<5".into(), "".into())
    } else {
        (c.count.to_string(), c.bytes.to_string())
    }
}

fn csv_field(s: &str) -> String {
    // Camera make/model come from EXIF; strip anything that is not a plain printable character.
    let s: String = s.chars().filter(|c| c.is_ascii_graphic() || *c == ' ').take(40).collect();
    if s.contains(',') || s.contains('"') {
        format!("\"{}\"", s.replace('"', "\"\""))
    } else {
        s
    }
}

fn render(o: &Opts, t: &Totals, secs: f64) -> Vec<(String, String)> {
    let mut files = Vec::new();
    let mut s = String::from("category,ext_group,log2_bin,count,bytes\n");
    for ((c, g, b), cell) in &t.local {
        let (n, by) = cell_str(cell);
        s += &format!("{c},{g},{b},{n},{by}\n");
    }
    files.push(("census_local.csv".into(), s));
    let mut s = String::from("category,ext_group,log2_bin,count,bytes\n");
    for ((c, g, b), cell) in &t.cloud {
        let (n, by) = cell_str(cell);
        s += &format!("{c},{g},{b},{n},{by}\n");
    }
    files.push(("census_cloud_only.csv".into(), s));
    let mut s = String::from("location_class,state,category,count,bytes\n");
    for ((l, st, c), cell) in &t.locations {
        let (n, by) = cell_str(cell);
        s += &format!("{l},{st},{c},{n},{by}\n");
    }
    files.push(("census_locations.csv".into(), s));
    let mut s = String::from("category,month,source,count,bytes\n");
    for ((c, m, src), cell) in &t.months {
        let (n, by) = cell_str(cell);
        s += &format!("{c},{m},{src},{n},{by}\n");
    }
    files.push(("census_months.csv".into(), s));
    if o.exif {
        let mut s = String::from("make,model,count,bytes\n");
        for ((mk, md), cell) in &t.cameras {
            let (n, by) = cell_str(cell);
            s += &format!("{},{},{n},{by}\n", csv_field(mk), csv_field(md));
        }
        files.push(("census_cameras.csv".into(), s));
    }
    let local_bytes: u64 = t.local.values().map(|c| c.bytes).sum();
    let cloud_bytes: u64 = t.cloud.values().map(|c| c.bytes).sum();
    let s = format!(
        "key,value\ncensus_version,{VERSION}\nos,{}\narch,{}\nroots,{}\nsniff,{}\nexif,{}\nelapsed_seconds,{:.1}\n\
         files,{}\ndirs,{}\nlocal_bytes,{}\ncloud_only_files,{}\ncloud_only_logical_bytes,{}\nsymlinks_skipped,{}\n\
         other_filesystems_skipped,{}\nunreadable_dirs,{}\nunreadable_entries,{}\nsniffed_files,{}\nexif_parsed,{}\nexif_failed,{}\n",
        std::env::consts::OS,
        std::env::consts::ARCH,
        o.roots.len(),
        o.sniff,
        o.exif,
        secs,
        t.files,
        t.dirs,
        local_bytes,
        t.placeholders,
        cloud_bytes,
        t.symlinks_skipped,
        t.other_fs_skipped,
        t.unreadable_dirs,
        t.unreadable_entries,
        t.sniffed,
        t.exif_ok,
        t.exif_fail
    );
    files.push(("census_device.csv".into(), s));
    files
}

fn human(b: u64) -> String {
    let gb = b as f64 / 1e9;
    if gb >= 1.0 { format!("{gb:.1} GB") } else { format!("{:.0} MB", b as f64 / 1e6) }
}

fn summary(t: &Totals) -> String {
    let mut by_cat: BTreeMap<&str, Cell> = BTreeMap::new();
    for ((c, _, _), cell) in &t.local {
        let e = by_cat.entry(c.as_str()).or_default();
        e.count += cell.count;
        e.bytes += cell.bytes;
    }
    let mut s = String::from("\nIn plain words (on this device, stored locally):\n");
    for k in ["photo", "raw", "video", "audio", "document", "email", "genealogy", "archive"] {
        if let Some(c) = by_cat.get(k) {
            s += &format!("  {:<10} {:>9} files  {:>10}\n", k, c.count, human(c.bytes));
        }
    }
    if t.placeholders > 0 {
        let b: u64 = t.cloud.values().map(|c| c.bytes).sum();
        s += &format!("  cloud-only (not on this device, only in the cloud): {} files, {}\n", t.placeholders, human(b));
    }
    s
}

fn parse_args() -> Opts {
    let mut o = Opts {
        roots: vec![],
        out: PathBuf::from("census-output"),
        sniff: true,
        exif: false,
        yes: false,
        one_fs: true,
        list_candidates: false,
    };
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--root" => o.roots.push(PathBuf::from(it.next().expect("--root needs a path"))),
            "--out" => o.out = PathBuf::from(it.next().expect("--out needs a path")),
            "--no-sniff" => o.sniff = false,
            "--exif" => o.exif = true,
            "--yes" => o.yes = true,
            "--cross-filesystems" => o.one_fs = false,
            "--list-candidate-folders" => o.list_candidates = true,
            "-h" | "--help" => {
                eprintln!(
                    "census [--root DIR]... [--out DIR] [--exif] [--no-sniff] [--cross-filesystems] \
                     [--list-candidate-folders] [--yes]\nDefault root: the home folder."
                );
                std::process::exit(0);
            }
            x => {
                eprintln!("unknown argument: {x}");
                std::process::exit(2);
            }
        }
    }
    if o.roots.is_empty() {
        let home = std::env::var_os("HOME").or_else(|| std::env::var_os("USERPROFILE")).expect("no home folder");
        o.roots.push(PathBuf::from(home));
    }
    o
}

fn main() {
    let o = parse_args();
    let mut t = Totals::default();
    eprintln!("Counting files. Nothing is opened except files with no known type{}.",
        if o.exif { " and photos/videos (for their date and camera model)" } else { "" });
    let start = Instant::now();
    walk(&o, &mut t);
    let secs = start.elapsed().as_secs_f64();
    let files = render(&o, &t, secs);

    println!("===== EXACTLY what would be saved (nothing else leaves this device) =====");
    for (name, body) in &files {
        println!("--- {name} ---\n{body}");
    }
    println!("{}", summary(&t));
    println!("Counted {} files in {:.1} s.", t.files, secs);

    if o.list_candidates {
        // Local screen only (H3 R6/R11): never written to the output folder.
        eprintln!("\n[ON THIS SCREEN ONLY - NOT SAVED] Folders outside the usual places with 20+ photos or videos:");
        let mut v: Vec<_> = t.candidates.iter().filter(|(_, n)| **n >= 20).collect();
        v.sort_by(|a, b| b.1.cmp(a.1));
        for (p, n) in v.iter().take(15) {
            eprintln!("  {n:>6}  {}", p.display());
        }
        eprintln!("[END OF LOCAL-ONLY LIST] Only the count of such folders is kept: {}", v.len());
    }

    let ok = if o.yes {
        true
    } else {
        print!("\nSave these totals to the folder '{}'? Type yes or no: ", o.out.display());
        io::stdout().flush().ok();
        let mut line = String::new();
        io::stdin().read_line(&mut line).ok();
        line.trim().eq_ignore_ascii_case("yes") || line.trim().eq_ignore_ascii_case("y")
    };
    if !ok {
        println!("Nothing was saved.");
        return;
    }
    fs::create_dir_all(&o.out).expect("cannot create output folder");
    for (name, body) in &files {
        fs::write(o.out.join(name), body).expect("cannot write output");
    }
    if o.list_candidates {
        let n = t.candidates.values().filter(|n| **n >= 20).count();
        fs::write(o.out.join("census_candidate_folders.csv"), format!("key,value\ncandidate_media_folders_outside_usual_places,{n}\n"))
            .expect("cannot write output");
    }
    println!("Saved to '{}'. Hand this folder over; this program never sends anything itself.", o.out.display());
}
