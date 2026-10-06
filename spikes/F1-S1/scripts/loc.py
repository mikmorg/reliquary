#!/usr/bin/env python3
"""F1-S1 size measurement: tokei code-line counts per candidate component.

Counts *code* lines (tokei's "code", no comments/blanks). Product code and test code are
counted separately. Generated code is excluded by the globs in EXCLUDE_GEN (and listed in the
output so the reader can judge). Usage: loc.py <src-root> > loc.csv
"""
import json, subprocess, sys, os, csv

ROOT = sys.argv[1]
EXCLUDE_GEN = ["*.g.dart", "*.freezed.dart", "*.gr.dart", "*.pb.go", "*.pb.dart", "*.pbenum.dart",
               "*.pbjson.dart", "*.pbserver.dart", "**/openapi/**", "**/generated/**", "**/l10n/**",
               "**/intl/**", "*.lock", "**/node_modules/**", "**/*.min.js", "**/vendor/**",
               "**/drift_schemas/**", "**/i18n/**", "**/locales/**", "**/translations/**",
               "*.json", "*.yaml", "*.yml", "*.xml", "*.svg", "*.md", "*.txt", "*.html", "*.css", "*.scss",
               "*.plist", "*.pbxproj", "*.storyboard", "*.xib", "*.strings", "*.arb", "*.po", "*.rst",
               "*.toml", "*.sql", "*.csv", "*.ini", "*.cfg"]
TEST_GLOBS = ["**/test/**", "**/tests/**", "**/testing/**", "**/integration_test/**", "**/test_driver/**",
              "**/testdata/**", "**/mobile-tests/**", "**/e2e/**", "**/__tests__/**", "*_test.go",
              "*.spec.ts", "*.test.ts", "*.spec.tsx", "*.test.tsx", "*_test.dart", "**/testsuite/**",
              "**/*Test.java", "**/*Test.kt", "**/androidTest/**", "**/UnitTests/**", "**/Duplicati.UnitTest/**",
              "**/testutil/**", "**/conftest.py", "**/*_tests.rs"]

# label, path relative to ROOT, description
COMPONENTS = [
  ("ente-photos-mobile-dart", "ente/mobile/apps/photos/lib", "Ente Photos Flutter app (Dart, lib/ only)"),
  ("ente-photos-mobile-native", "ente/mobile/apps/photos/android ente/mobile/apps/photos/ios ente/mobile/apps/photos/plugins", "Ente Photos native Android/iOS glue + in-app plugins"),
  ("ente-mobile-shared-packages", "ente/mobile/packages", "Ente shared Flutter packages (crypto, accounts, network, ui...)"),
  ("ente-rust", "ente/rust", "Ente Rust crates (core/bindings)"),
  ("ente-museum-server", "ente/server", "Ente museum server (Go)"),
  ("ente-web", "ente/web", "Ente web apps + packages (TS; also the desktop app's UI)"),
  ("immich-mobile-dart", "immich/mobile/lib", "Immich Flutter app (Dart, lib/ only, openapi excluded)"),
  ("immich-mobile-native", "immich/mobile/android immich/mobile/ios immich/mobile/packages", "Immich native Android/iOS code + local packages"),
  ("immich-server", "immich/server/src", "Immich server (TypeScript, NestJS)"),
  ("immich-web", "immich/web/src", "Immich web (Svelte/TS)"),
  ("immich-ml", "immich/machine-learning", "Immich ML service (Python)"),
  ("restic", "restic_restic", "restic CLI + repository library (Go)"),
  ("kopia", "kopia_kopia", "Kopia CLI, repository, server, UI glue (Go)"),
  ("kopia-server-only", "kopia_kopia/internal/server kopia_kopia/internal/grpcapi kopia_kopia/internal/auth", "Kopia repository-server + ACL code (Go)"),
  ("plakar", "PlakarKorp_plakar", "Plakar (Go)"),
  ("plakar-kloset", "kloset", "Kloset storage engine library used by Plakar (Go)"),
  ("syncthing", "syncthing_syncthing", "Syncthing (Go)"),
  ("syncthing-android-fork", "researchxxl_syncthing-android", "Syncthing-Fork Android wrapper (Java/Kotlin)"),
  ("rustic_core", "rustic-rs_rustic_core", "rustic_core library (Rust)"),
  ("rustic-cli", "rustic-rs_rustic", "rustic CLI (Rust)"),
  ("borg", "borgbackup_borg/src", "Borg (Python + Cython/C)"),
  ("urbackup-backend", "uroni_urbackup_backend", "UrBackup server+client backend (C++)"),
  ("duplicati", "duplicati_duplicati", "Duplicati (C#)"),
  ("nextcloud-android", "nextcloud_android", "Nextcloud Android client (Java/Kotlin)"),
  ("reliquary-spike-content-encryption", os.environ.get("RELIQUARY_SPIKE", "/home/user/reliquary/spikes/content-encryption"), "Reliquary throwaway encryption spike (Rust+Go+Python)"),
]

def tokei(paths, excludes):
    cmd = ["tokei", "--output", "json"]
    for e in excludes:
        cmd += ["-e", e]
    cmd += paths
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out)

def summarise(j):
    total = 0; langs = {}
    for lang, v in j.items():
        if lang == "Total": continue
        c = v.get("code", 0)
        # include embedded children (e.g. code blocks) only via top-level code count
        if c: langs[lang] = c; total += c
    return total, langs

w = csv.writer(sys.stdout)
w.writerow(["component", "paths", "commit", "product_code_lines", "test_code_lines", "top_languages_product", "description"])
for label, rel, desc in COMPONENTS:
    paths = [p if p.startswith("/") else os.path.join(ROOT, p) for p in rel.split()]
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        w.writerow([label, rel, "", "", "", "missing", desc]); continue
    repo = paths[0]
    commit = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%h"], capture_output=True, text=True).stdout.strip()
    prod_total, prod_langs = summarise(tokei(paths, EXCLUDE_GEN + TEST_GLOBS))
    all_total, _ = summarise(tokei(paths, EXCLUDE_GEN))
    top = "; ".join(f"{k}={v}" for k, v in sorted(prod_langs.items(), key=lambda kv: -kv[1])[:4])
    w.writerow([label, rel, commit, prod_total, all_total - prod_total, top, desc])
    sys.stdout.flush()
