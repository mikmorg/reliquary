// THROWAWAY SPIKE CODE (Reliquary A6, Wave 1). Not production code.
//
// ocfl.go: minimal OCFL 1.1 writer for the "same age objects in an OCFL storage
// root" variant. One OCFL object per stored content object, one version (v1),
// storage layout extension 0003-hash-and-id-n-tuple-storage-layout (defaults; the
// encapsulation directory is the object ID, i.e. the plaintext SHA-256 in hex).
// (0004 was tried first; ocfl-py 2.1.0 cannot validate a 0004 storage root, E071.)
// Object ID = lowercase hex SHA-256 of the plaintext (the Reliquary content key).
package main

import (
	"crypto/sha256"
	"crypto/sha512"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func initOCFLRoot(root string) error {
	if err := ensureDir(root); err != nil {
		return err
	}
	if err := writeFileDurable(filepath.Join(root, "0=ocfl_1.1"), []byte("ocfl_1.1\n")); err != nil {
		return err
	}
	layout := map[string]string{
		"extension":   "0003-hash-and-id-n-tuple-storage-layout",
		"description": "Hashed Truncated N-tuple Trees with Object ID Encapsulating Directory for OCFL Storage Hierarchies",
	}
	b, _ := json.MarshalIndent(layout, "", "  ")
	if err := writeFileDurable(filepath.Join(root, "ocfl_layout.json"), b); err != nil {
		return err
	}
	ext := filepath.Join(root, "extensions", "0003-hash-and-id-n-tuple-storage-layout")
	if err := ensureDir(ext); err != nil {
		return err
	}
	cfg := map[string]any{"extensionName": "0003-hash-and-id-n-tuple-storage-layout", "digestAlgorithm": "sha256",
		"tupleSize": 3, "numberOfTuples": 3}
	b, _ = json.MarshalIndent(cfg, "", "  ")
	return writeFileDurable(filepath.Join(ext, "config.json"), b)
}

func ocflObjectRoot(root, id string) string {
	d := sha256.Sum256([]byte(id))
	h := hex.EncodeToString(d[:])
	return filepath.Join(root, h[0:3], h[3:6], h[6:9], id) // id is [0-9a-f]: no percent-encoding needed
}

type ocflInventory struct {
	ID               string                         `json:"id"`
	Type             string                         `json:"type"`
	DigestAlgorithm  string                         `json:"digestAlgorithm"`
	Head             string                         `json:"head"`
	ContentDirectory string                         `json:"contentDirectory"`
	Manifest         map[string][]string            `json:"manifest"`
	Versions         map[string]ocflVersion         `json:"versions"`
	Fixity           map[string]map[string][]string `json:"fixity,omitempty"`
}

type ocflVersion struct {
	Created string              `json:"created"`
	State   map[string][]string `json:"state"`
	Message string              `json:"message"`
	User    map[string]string   `json:"user"`
}

func writeSmall(path string, data []byte) error {
	f, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	if _, err := f.Write(data); err != nil {
		f.Close()
		return err
	}
	if err := fsyncFile(f); err != nil {
		f.Close()
		return err
	}
	return f.Close()
}

// ocflCommit builds a complete object directory around the already-written,
// fsynced content temp file, then renames the whole directory into place.
func (s *Store) ocflCommit(contentTmp, id, st512, st256 string) error {
	root := filepath.Join(s.Root, "ocfl")
	objTmp := filepath.Join(s.Root, "tmp", "obj-"+randHex(8))
	cdir := filepath.Join(objTmp, "v1", "content")
	if err := os.MkdirAll(cdir, 0o700); err != nil {
		return err
	}
	name := id + ".age"
	if err := os.Rename(contentTmp, filepath.Join(cdir, name)); err != nil {
		return err
	}
	cpath := "v1/content/" + name
	inv := ocflInventory{
		ID: id, Type: "https://ocfl.io/1.1/spec/#inventory", DigestAlgorithm: "sha512", Head: "v1",
		ContentDirectory: "content",
		Manifest:         map[string][]string{st512: {cpath}},
		Versions: map[string]ocflVersion{"v1": {
			Created: time.Now().UTC().Format(time.RFC3339),
			State:   map[string][]string{st512: {name}},
			Message: "Reliquary ingest (A6 spike)",
			User:    map[string]string{"name": "reliquary-ingest", "address": "urn:reliquary:homelab"},
		}},
		Fixity: map[string]map[string][]string{"sha256": {st256: {cpath}}},
	}
	ib, _ := json.MarshalIndent(inv, "", "  ")
	is := sha512.Sum512(ib)
	side := []byte(hex.EncodeToString(is[:]) + "  inventory.json\n")
	for _, d := range []string{objTmp, filepath.Join(objTmp, "v1")} {
		if err := writeSmall(filepath.Join(d, "inventory.json"), ib); err != nil {
			return err
		}
		if err := writeSmall(filepath.Join(d, "inventory.json.sha512"), side); err != nil {
			return err
		}
	}
	if err := writeSmall(filepath.Join(objTmp, "0=ocfl_object_1.1"), []byte("ocfl_object_1.1\n")); err != nil {
		return err
	}
	for _, d := range []string{cdir, filepath.Join(objTmp, "v1"), objTmp} {
		if err := fsyncDir(d); err != nil {
			return err
		}
	}
	final := ocflObjectRoot(root, id)
	if err := ensureDir(filepath.Dir(final)); err != nil {
		return err
	}
	if _, err := os.Stat(final); err == nil {
		os.RemoveAll(final) // uncommitted leftover (no manifest line): replace
	}
	maybeCrash("ocfl-objdir-built")
	if err := os.Rename(objTmp, final); err != nil {
		return err
	}
	maybeCrash("renamed-before-dirsync")
	if err := fsyncDir(filepath.Dir(final)); err != nil {
		return err
	}
	return fsyncDir(filepath.Join(s.Root, "tmp"))
}

func walkOCFLObjects(root string, fn func(objRoot, id string)) {
	filepath.WalkDir(root, func(p string, d os.DirEntry, e error) error {
		if e != nil || d.IsDir() || d.Name() != "0=ocfl_object_1.1" {
			return nil
		}
		objRoot := filepath.Dir(p)
		b, err := os.ReadFile(filepath.Join(objRoot, "inventory.json"))
		id := ""
		if err == nil {
			var inv ocflInventory
			if json.Unmarshal(b, &inv) == nil {
				id = inv.ID
			}
		}
		if id == "" {
			id = strings.TrimSpace(filepath.Base(objRoot))
		}
		fn(objRoot, id)
		return filepath.SkipDir
	})
}
