// THROWAWAY SPIKE CODE (Reliquary A6, Wave 1). Not production code.
//
// store.go: the "plain CAS of age v1 objects" layout (and an OCFL 1.1 variant),
// with the A' header rewrap and the durable-write ordering under test.
package main

import (
	"bufio"
	mrand "math/rand/v2"
	"syscall"
	"bytes"
	"crypto/hkdf"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/sha512"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"hash"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"filippo.io/age"
)

var b64 = base64.RawStdEncoding

// Durability switch. -nofsync turns every fsync off; used only as the negative
// control that proves the LazyFS harness can detect lost acknowledged items.
var doFsync = true

// Crash-point injection for A6-S3: A6CAS_CRASHPOINT=<name>|any, A6CAS_CRASH_PROB=<p>.
// At a matching point the process SIGKILLs itself (no cleanup, like kill -9).
var crashPoint = os.Getenv("A6CAS_CRASHPOINT")
var crashProb = func() float64 {
	var p float64
	fmt.Sscanf(os.Getenv("A6CAS_CRASH_PROB"), "%g", &p)
	return p
}()

func maybeCrash(name string) {
	if crashPoint != "" && (crashPoint == "any" || crashPoint == name) && mrand.Float64() < crashProb {
		fmt.Fprintf(os.Stderr, "CRASHPOINT %s\n", name)
		syscall.Kill(os.Getpid(), syscall.SIGKILL)
		select {}
	}
}

func maybeCrashForce(name string) {
	fmt.Fprintf(os.Stderr, "CRASHPOINT %s\n", name)
	syscall.Kill(os.Getpid(), syscall.SIGKILL)
	select {}
}

func fsyncFile(f *os.File) error {
	if !doFsync {
		return nil
	}
	return f.Sync()
}

func fsyncDir(dir string) error {
	if !doFsync {
		return nil
	}
	d, err := os.Open(dir)
	if err != nil {
		return err
	}
	defer d.Close()
	return d.Sync()
}

// ensureDir creates each missing component of dir and fsyncs its parent.
func ensureDir(dir string) error {
	if st, err := os.Stat(dir); err == nil && st.IsDir() {
		return nil
	}
	parent := filepath.Dir(dir)
	if err := ensureDir(parent); err != nil {
		return err
	}
	if err := os.Mkdir(dir, 0o700); err != nil && !errors.Is(err, os.ErrExist) {
		return err
	}
	return fsyncDir(parent)
}

type Store struct {
	Root   string
	Layout string // "cas" or "ocfl"
	man    *os.File
	// in-memory view of the manifest (rebuilt at open)
	Blobs   map[string]ManLine
	Records map[string]ManLine
}

type ManLine struct {
	T            string `json:"t"` // "blob" | "record"
	SHA256       string `json:"sha256,omitempty"`
	Size         int64  `json:"size,omitempty"`
	RecordID     string `json:"record_id,omitempty"`
	MetaSHA256   string `json:"meta_sha256,omitempty"`
	StoredSHA256 string `json:"stored_sha256"`
	StoredSize   int64  `json:"stored_size"`
	OCFLSHA512   string `json:"ocfl_sha512,omitempty"`
	H0           string `json:"h0,omitempty"`         // original device-written header of the stored object (b64)
	ContentH0    string `json:"content_h0,omitempty"` // record lines: header of this record's own content upload
	Epoch        int    `json:"epoch"`
	At           int64  `json:"at"`
}

const layoutDecl = `REL-STORE-v0 (Reliquary A6 spike layout; THROWAWAY)
blobs/<aa>/<bb>/<sha256>.age   content object: standard age v1 file; <sha256> = SHA-256 of the PLAINTEXT
                               (cas layout; the ocfl layout puts objects under ocfl/ instead)
records/<rr>/<record_id>.age   device-signed metadata record: standard age v1 file
manifest/manifest.jsonl        append-only; one JSON line per committed blob/record with
                               stored_sha256 (SHA-256 of the stored file bytes, for keyless audits),
                               h0 (original device header, base64) and commit time
devices/devices.json           device registry (device_id -> person, Ed25519 public key)
Decrypt any .age file with: age -d -i archive.key FILE
`

func InitStore(root, layout string) error {
	for _, d := range []string{"blobs", "records", "manifest", "tmp", "quarantine", "devices"} {
		if err := ensureDir(filepath.Join(root, d)); err != nil {
			return err
		}
	}
	if layout == "ocfl" {
		if err := initOCFLRoot(filepath.Join(root, "ocfl")); err != nil {
			return err
		}
	}
	return writeFileDurable(filepath.Join(root, "REL-STORE-v0"), []byte(layoutDecl+"layout="+layout+"\n"))
}

func writeFileDurable(path string, data []byte) error {
	tmp := path + ".tmp"
	f, err := os.OpenFile(tmp, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o600)
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
	f.Close()
	if err := os.Rename(tmp, path); err != nil {
		return err
	}
	return fsyncDir(filepath.Dir(path))
}

// LockStore takes the single-writer lock (flock on store/LOCK). Added after the
// first A6-S4 run showed that two concurrent ingest processes write duplicate
// manifest lines and overwrite each other's blob files (see README).
// The *os.File must stay reachable: the first version kept it in a local variable,
// the garbage collector's finalizer closed the fd and the flock was silently released
// (found by the second A6-S4 run, see README).
var lockFile *os.File

func LockStore(root string) error {
	f, err := os.OpenFile(filepath.Join(root, "LOCK"), os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return err
	}
	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		f.Close()
		return fmt.Errorf("store is locked by another writer: %w", err)
	}
	lockFile = f
	return nil
}

func OpenStore(root string) (*Store, error) {
	decl, err := os.ReadFile(filepath.Join(root, "REL-STORE-v0"))
	if err != nil {
		return nil, err
	}
	layout := "cas"
	if strings.Contains(string(decl), "layout=ocfl") {
		layout = "ocfl"
	}
	s := &Store{Root: root, Layout: layout, Blobs: map[string]ManLine{}, Records: map[string]ManLine{}}
	mp := filepath.Join(root, "manifest", "manifest.jsonl")
	if _, err := repairManifest(mp); err != nil {
		return nil, err
	}
	lines, err := readManifest(mp)
	if err != nil {
		return nil, err
	}
	for _, l := range lines {
		switch l.T {
		case "blob":
			s.Blobs[l.SHA256] = l
		case "record":
			s.Records[l.RecordID] = l
		}
	}
	s.man, err = os.OpenFile(mp, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return nil, err
	}
	return s, fsyncDir(filepath.Dir(mp))
}

// repairManifest truncates a torn (newline-less) final line. Returns bytes removed.
func repairManifest(path string) (int, error) {
	data, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return 0, nil
	}
	if err != nil {
		return 0, err
	}
	if len(data) == 0 || data[len(data)-1] == '\n' {
		return 0, nil
	}
	cut := bytes.LastIndexByte(data, '\n') + 1
	if err := os.Truncate(path, int64(cut)); err != nil {
		return 0, err
	}
	f, err := os.OpenFile(path, os.O_WRONLY, 0)
	if err == nil {
		fsyncFile(f)
		f.Close()
	}
	return len(data) - cut, nil
}

func readManifest(path string) ([]ManLine, error) {
	f, err := os.Open(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var out []ManLine
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1<<20), 1<<24)
	n := 0
	for sc.Scan() {
		n++
		var l ManLine
		if err := json.Unmarshal(sc.Bytes(), &l); err != nil {
			return nil, fmt.Errorf("manifest line %d: %w", n, err)
		}
		out = append(out, l)
	}
	return out, sc.Err()
}

func (s *Store) appendManifest(l ManLine) error {
	b, err := json.Marshal(l)
	if err != nil {
		return err
	}
	b = append(b, '\n')
	if crashPoint != "" && (crashPoint == "any" || crashPoint == "manifest-torn") && mrand.Float64() < crashProb {
		s.man.Write(b[:len(b)/2]) // torn line
		fsyncFile(s.man)
		maybeCrashForce("manifest-torn")
	}
	if _, err := s.man.Write(b); err != nil {
		return err
	}
	return fsyncFile(s.man)
}

func (s *Store) BlobPath(sha string) string {
	if s.Layout == "ocfl" {
		return filepath.Join(ocflObjectRoot(filepath.Join(s.Root, "ocfl"), sha), "v1", "content", sha+".age")
	}
	return filepath.Join(s.Root, "blobs", sha[0:2], sha[2:4], sha+".age")
}

func (s *Store) RecordPath(rid string) string {
	return filepath.Join(s.Root, "records", rid[0:2], rid+".age")
}

// ---- age header helpers (written from the C2SP age spec; same approach as D2-S2) ----

// splitHeader returns the exact header bytes of an age v1 file and checks that
// they are canonical (re-marshal equals the raw prefix).
func splitHeader(path string) ([]byte, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	hb, err := age.ExtractHeader(bufio.NewReader(f))
	if err != nil {
		return nil, err
	}
	raw := make([]byte, len(hb))
	if _, err := f.ReadAt(raw, 0); err != nil {
		return nil, err
	}
	if !bytes.Equal(raw, hb) {
		return nil, errors.New("non-canonical age header")
	}
	return raw, nil
}

func headerMAC(h []byte) string {
	i := bytes.LastIndex(h, []byte("\n--- "))
	return strings.TrimSpace(string(h[i+5:]))
}

func marshalStanza(w *bytes.Buffer, st *age.Stanza) {
	w.WriteString("-> ")
	w.WriteString(st.Type)
	for _, a := range st.Args {
		w.WriteString(" ")
		w.WriteString(a)
	}
	w.WriteString("\n")
	enc := b64.EncodeToString(st.Body)
	for len(enc) >= 64 {
		w.WriteString(enc[:64])
		w.WriteString("\n")
		enc = enc[64:]
	}
	w.WriteString(enc)
	w.WriteString("\n")
}

func macOver(fileKey, upToDashes []byte) ([]byte, error) {
	k, err := hkdf.Key(sha256.New, fileKey, nil, "header", 32)
	if err != nil {
		return nil, err
	}
	m := hmac.New(sha256.New, k)
	m.Write(upToDashes)
	return m.Sum(nil), nil
}

// buildHeader writes a fresh age v1 header for fileKey to the given recipients.
func buildHeader(fileKey []byte, rcpts []age.Recipient) ([]byte, error) {
	var buf bytes.Buffer
	buf.WriteString("age-encryption.org/v1\n")
	for _, r := range rcpts {
		sts, err := r.Wrap(fileKey)
		if err != nil {
			return nil, err
		}
		for _, st := range sts {
			marshalStanza(&buf, st)
		}
	}
	buf.WriteString("---")
	mac, err := macOver(fileKey, buf.Bytes())
	if err != nil {
		return nil, err
	}
	buf.WriteString(" " + b64.EncodeToString(mac) + "\n")
	return buf.Bytes(), nil
}

// verifyHeaderMAC recomputes the MAC of header h under fileKey.
func verifyHeaderMAC(h, fileKey []byte) (bool, error) {
	i := bytes.LastIndex(h, []byte("\n---"))
	if i < 0 {
		return false, errors.New("no MAC line")
	}
	mac, err := macOver(fileKey, h[:i+4])
	if err != nil {
		return false, err
	}
	return b64.EncodeToString(mac) == headerMAC(h), nil
}

// rewrapTo writes header(new recipients) + payload(src from offset len(h0)) to w.
func rewrapCopy(w io.Writer, src *os.File, h0 []byte, ingest age.Identity, rcpts []age.Recipient) (newHdr []byte, err error) {
	fk, err := age.DecryptHeader(h0, ingest)
	if err != nil {
		return nil, fmt.Errorf("unwrap with ingest key: %w", err)
	}
	newHdr, err = buildHeader(fk, rcpts)
	for i := range fk {
		fk[i] = 0
	}
	if err != nil {
		return nil, err
	}
	if _, err := w.Write(newHdr); err != nil {
		return nil, err
	}
	if _, err := src.Seek(int64(len(h0)), io.SeekStart); err != nil {
		return nil, err
	}
	if _, err := io.Copy(w, src); err != nil {
		return nil, err
	}
	return newHdr, nil
}

func randHex(n int) string {
	b := make([]byte, n)
	rand.Read(b)
	return hex.EncodeToString(b)
}

type multiHash struct {
	s256 hash.Hash
	s512 hash.Hash
	n    int64
}

func (m *multiHash) Write(p []byte) (int, error) {
	m.s256.Write(p)
	if m.s512 != nil {
		m.s512.Write(p)
	}
	m.n += int64(len(p))
	return len(p), nil
}

// writeObject performs: O_EXCL temp in store/tmp, write, fsync, [ocfl wrap], rename, dir fsync.
// It returns stored sha256/sha512/size and the new header.
func (s *Store) writeObject(final string, src *os.File, h0 []byte, ingest age.Identity, rcpts []age.Recipient, isBlob bool, sha string) (st256, st512 string, stSize int64, err error) {
	tmpDir := filepath.Join(s.Root, "tmp")
	tmp := filepath.Join(tmpDir, randHex(8)+".part")
	f, err := os.OpenFile(tmp, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		return
	}
	mh := &multiHash{s256: sha256.New()}
	if s.Layout == "ocfl" && isBlob {
		mh.s512 = sha512.New()
	}
	bw := bufio.NewWriterSize(f, 1<<20)
	if _, err = rewrapCopy(io.MultiWriter(bw, mh), src, h0, ingest, rcpts); err != nil {
		f.Close()
		os.Remove(tmp)
		return
	}
	if err = bw.Flush(); err != nil {
		f.Close()
		return
	}
	maybeCrash("tmp-written-unsynced")
	if err = fsyncFile(f); err != nil {
		f.Close()
		return
	}
	f.Close()
	maybeCrash("tmp-synced")
	st256 = hex.EncodeToString(mh.s256.Sum(nil))
	stSize = mh.n
	if mh.s512 != nil {
		st512 = hex.EncodeToString(mh.s512.Sum(nil))
	}
	if s.Layout == "ocfl" && isBlob {
		err = s.ocflCommit(tmp, sha, st512, st256)
		return
	}
	if err = ensureDir(filepath.Dir(final)); err != nil {
		return
	}
	if err = os.Rename(tmp, final); err != nil {
		return
	}
	maybeCrash("renamed-before-dirsync")
	err = fsyncDir(filepath.Dir(final))
	maybeCrash("renamed-before-manifest")
	return
}

// PutBlob: idempotent. Returns (alreadyPresent, error).
func (s *Store) PutBlob(sha string, size int64, src *os.File, h0 []byte, ingest age.Identity, rcpts []age.Recipient, epoch int) (bool, error) {
	if _, ok := s.Blobs[sha]; ok {
		return true, nil // committed earlier: equal content is a success (A3 F6 step 3)
	}
	st256, st512, stSize, err := s.writeObject(s.BlobPath(sha), src, h0, ingest, rcpts, true, sha)
	if err != nil {
		return false, err
	}
	l := ManLine{T: "blob", SHA256: sha, Size: size, StoredSHA256: st256, StoredSize: stSize, OCFLSHA512: st512,
		H0: b64.EncodeToString(h0), Epoch: epoch, At: time.Now().UnixNano()}
	if err := s.appendManifest(l); err != nil {
		return false, err
	}
	s.Blobs[sha] = l
	return false, nil
}

func (s *Store) ArchiveRecord(rid, metaSHA string, src *os.File, h0 []byte, contentH0 []byte, ingest age.Identity, rcpts []age.Recipient, epoch int) (ManLine, bool, error) {
	if l, ok := s.Records[rid]; ok {
		if l.MetaSHA256 != metaSHA {
			return l, true, fmt.Errorf("record %s re-sent with different bytes (clone or bug, H-13)", rid)
		}
		return l, true, nil
	}
	st256, _, stSize, err := s.writeObject(s.RecordPath(rid), src, h0, ingest, rcpts, false, "")
	if err != nil {
		return ManLine{}, false, err
	}
	l := ManLine{T: "record", RecordID: rid, MetaSHA256: metaSHA, StoredSHA256: st256, StoredSize: stSize,
		H0: b64.EncodeToString(h0), Epoch: epoch, At: time.Now().UnixNano()}
	if contentH0 != nil {
		l.ContentH0 = b64.EncodeToString(contentH0)
	}
	if err := s.appendManifest(l); err != nil {
		return ManLine{}, false, err
	}
	s.Records[rid] = l
	return l, false, nil
}

// Recover: delete temp files, quarantine object files that have no manifest line.
func (s *Store) Recover() (tmpRemoved, quarantined int, err error) {
	ents, _ := os.ReadDir(filepath.Join(s.Root, "tmp"))
	for _, e := range ents {
		os.RemoveAll(filepath.Join(s.Root, "tmp", e.Name()))
		tmpRemoved++
	}
	if tmpRemoved > 0 {
		fsyncDir(filepath.Join(s.Root, "tmp"))
	}
	q := func(path string) {
		dst := filepath.Join(s.Root, "quarantine", fmt.Sprintf("%d-%s", time.Now().UnixNano(), filepath.Base(path)))
		os.Rename(path, dst)
		quarantined++
	}
	if s.Layout == "cas" {
		filepath.WalkDir(filepath.Join(s.Root, "blobs"), func(p string, d os.DirEntry, e error) error {
			if e == nil && !d.IsDir() {
				sha := strings.TrimSuffix(d.Name(), ".age")
				if _, ok := s.Blobs[sha]; !ok {
					q(p)
				}
			}
			return nil
		})
	} else {
		walkOCFLObjects(filepath.Join(s.Root, "ocfl"), func(objRoot, id string) {
			if _, ok := s.Blobs[id]; !ok {
				q(objRoot)
			}
		})
	}
	filepath.WalkDir(filepath.Join(s.Root, "records"), func(p string, d os.DirEntry, e error) error {
		if e == nil && !d.IsDir() {
			rid := strings.TrimSuffix(d.Name(), ".age")
			if _, ok := s.Records[rid]; !ok {
				q(p)
			}
		}
		return nil
	})
	if quarantined > 0 {
		fsyncDir(filepath.Join(s.Root, "quarantine"))
	}
	return
}
