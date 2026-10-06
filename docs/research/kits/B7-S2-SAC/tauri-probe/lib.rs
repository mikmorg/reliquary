// Replacement for src-tauri/src/lib.rs in a fresh `create-tauri-app` (Vanilla) project.
// NOT COMPILED IN THE RESEARCH CONTAINER. API names checked against the
// tauri-plugin-updater 2.13.0 source (UpdaterExt::updater, Updater::check,
// Update::download_and_install). On Windows, download_and_install writes the NSIS
// installer to %TEMP%\<app>-<version>-updater-*\ , launches it with ShellExecuteW
// ("/P /UPDATE" in passive mode) and exits this process.
//
// Each launch appends one line to %LOCALAPPDATA%\ReliquarySacProbe\probe.log so the
// tester can see which version actually ran, and what the updater did.

use std::io::Write;
use tauri_plugin_updater::UpdaterExt;

// Change this string between v1 and v2 so the app exe hash changes as in a real release.
const BUILD_MARKER: &str = "sac-probe build v1";

fn log_line(msg: &str) {
    let dir = std::env::var("LOCALAPPDATA")
        .map(|p| std::path::PathBuf::from(p).join("ReliquarySacProbe"))
        .unwrap_or_else(|_| std::env::temp_dir().join("ReliquarySacProbe"));
    let _ = std::fs::create_dir_all(&dir);
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir.join("probe.log"))
    {
        let t = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        let _ = writeln!(f, "{t} {msg}");
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            log_line(&format!(
                "started version={} marker={:?} exe={:?}",
                app.package_info().version,
                BUILD_MARKER,
                std::env::current_exe().ok()
            ));
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let updater = match handle.updater() {
                    Ok(u) => u,
                    Err(e) => return log_line(&format!("updater init error: {e}")),
                };
                match updater.check().await {
                    Ok(Some(update)) => {
                        log_line(&format!("update found: {}", update.version));
                        match update.download_and_install(|_, _| {}, || {}).await {
                            // On Windows the process exits inside download_and_install.
                            Ok(()) => {
                                log_line("installed; restarting");
                                handle.restart();
                            }
                            Err(e) => log_line(&format!("download/install error: {e}")),
                        }
                    }
                    Ok(None) => log_line("no update available"),
                    Err(e) => log_line(&format!("update check error: {e}")),
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
