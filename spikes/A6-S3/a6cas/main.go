// THROWAWAY SPIKE CODE (Reliquary A6, Wave 1). Not production code.
//
// a6cas: a plain content-addressed store of age v1 objects with the A' posture
// (header rewrap at ingest to an offline archive recipient), used by spikes
// A6-S3 (crash consistency), A6-S4 (catalog loss), A6-S5 (format independence),
// A6-S6 (rewrap round trip) and the A6-S2 bake-off kit.
//
//	a6cas keygen  -dir D [-pq]
//	a6cas gen     -out D -keys K -n N [-dup F] [-scale S] [-seed X]
//	a6cas stage   -src DIR -out D -keys K      (real files, e.g. the H3 corpus: stays on the homelab)
//	a6cas init    -store S [-layout cas|ocfl] -devices FILE
//	a6cas ingest  -store S -catalog C -staging D -ingest-key F -rcpt F [-epoch E] [-nofsync] [-limit N]
//	a6cas recover -store S -catalog C
//	a6cas audit   -store S                         (keyless)
//	a6cas rebuild -store S -out C -archive-key F [-no-manifest]
//	a6cas export  -catalog C [-mask]
//	a6cas get     -store S -archive-key F -sha256 H [-out F]
//	a6cas verify  -store S -archive-key F [-recovery-key F] [-ingest-key F]
package main

import (
	"bufio"
	"bytes"
	"crypto/ed25519"
	"crypto/hkdf"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	mrand "math/rand/v2"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"filippo.io/age"
)

func die(f string, a ...any) {
	fmt.Fprintf(os.Stderr, "a6cas: "+f+"\n", a...)
	os.Exit(1)
}

func must(err error) {
	if err != nil {
		die("%v", err)
	}
}

func loadIdentities(path string) []age.Identity {
	f, err := os.Open(path)
	must(err)
	defer f.Close()
	ids, err := age.ParseIdentities(f)
	must(err)
	return ids
}

func loadRecipients(path string) []age.Recipient {
	f, err := os.Open(path)
	must(err)
	defer f.Close()
	rs, err := age.ParseRecipients(f)
	must(err)
	return rs
}

func main() {
	if len(os.Args) < 2 {
		die("usage: see source header")
	}
	cmd, args := os.Args[1], os.Args[2:]
	switch cmd {
	case "keygen":
		cmdKeygen(args)
	case "gen":
		cmdGen(args)
	case "stage":
		cmdStage(args)
	case "init":
		fs := flag.NewFlagSet(cmd, flag.ExitOnError)
		st := fs.String("store", "", "")
		lay := fs.String("layout", "cas", "")
		dev := fs.String("devices", "", "")
		fs.Parse(args)
		must(InitStore(*st, *lay))
		b, err := os.ReadFile(*dev)
		must(err)
		must(writeFileDurable(filepath.Join(*st, "devices", "devices.json"), b))
	case "ingest":
		cmdIngest(args)
	case "recover":
		cmdRecover(args)
	case "audit":
		cmdAudit(args)
	case "rebuild":
		cmdRebuild(args)
	case "export":
		fs := flag.NewFlagSet(cmd, flag.ExitOnError)
		c := fs.String("catalog", "", "")
		mask := fs.Bool("mask", false, "")
		fs.Parse(args)
		db, err := OpenCatalog(*c)
		must(err)
		w := bufio.NewWriter(os.Stdout)
		must(exportCanonical(db, w, *mask))
		w.Flush()
	case "get":
		cmdGet(args)
	case "verify":
		cmdVerify(args)
	default:
		die("unknown command %s", cmd)
	}
}

// ---------------- keygen ----------------

func cmdKeygen(args []string) {
	fs := flag.NewFlagSet("keygen", flag.ExitOnError)
	dir := fs.String("dir", "", "")
	pq := fs.Bool("pq", false, "hybrid ML-KEM-768+X25519 archive/recovery identities")
	fs.Parse(args)
	must(os.MkdirAll(*dir, 0o700))
	gen := func(name string, hybrid bool) {
		var sk, pk string
		if hybrid {
			id, err := age.GenerateHybridIdentity()
			must(err)
			sk, pk = id.String(), id.Recipient().String()
		} else {
			id, err := age.GenerateX25519Identity()
			must(err)
			sk, pk = id.String(), id.Recipient().String()
		}
		must(os.WriteFile(filepath.Join(*dir, name+".key"), []byte(sk+"\n"), 0o600))
		must(os.WriteFile(filepath.Join(*dir, name+".pub"), []byte(pk+"\n"), 0o600))
	}
	gen("ingest-e1", false) // devices encrypt to this (CLAUDE.md "homelab public key", epoch 1)
	gen("archive", *pq)     // offline archive identity X
	gen("recovery", *pq)    // recovery recipient R (OD-08)
	a, _ := os.ReadFile(filepath.Join(*dir, "archive.pub"))
	r, _ := os.ReadFile(filepath.Join(*dir, "recovery.pub"))
	must(os.WriteFile(filepath.Join(*dir, "stored-recipients.txt"), append(a, r...), 0o600))
	fam := make([]byte, 32)
	for i := range fam {
		fam[i] = byte(mrand.Uint32())
	}
	must(os.WriteFile(filepath.Join(*dir, "family-secret.hex"), []byte(hex.EncodeToString(fam)+"\n"), 0o600))
}

// ---------------- gen (synthetic corpus, data class SYN) ----------------

type devInfo struct {
	Person string `json:"person"`
	Pub    string `json:"pub"`
}

func dedupID(fam []byte, sha []byte) string {
	dk, _ := hkdf.Key(sha256.New, fam, nil, "reliquary/v1/dedup-key/sha256-digest", 32)
	m := hmac.New(sha256.New, dk)
	m.Write(sha)
	return hex.EncodeToString(m.Sum(nil))
}

type chachaReader struct{ r *mrand.ChaCha8 }

func (c chachaReader) Read(p []byte) (int, error) { return c.r.Read(p) }

func cmdGen(args []string) {
	fs := flag.NewFlagSet("gen", flag.ExitOnError)
	out := fs.String("out", "", "")
	keys := fs.String("keys", "", "")
	n := fs.Int("n", 100, "")
	dup := fs.Float64("dup", 0.1, "fraction of records that are cross-device dedup hits")
	scale := fs.Float64("scale", 1.0, "multiply sizes")
	seed := fs.Uint64("seed", 1, "")
	ndev := fs.Int("devices", 6, "")
	fs.Parse(args)
	stg := filepath.Join(*out, "staging")
	must(os.MkdirAll(stg, 0o700))
	rng := mrand.New(mrand.NewPCG(*seed, 0xa6))
	famHex, err := os.ReadFile(filepath.Join(*keys, "family-secret.hex"))
	must(err)
	fam, _ := hex.DecodeString(strings.TrimSpace(string(famHex)))
	ingestR := loadRecipients(filepath.Join(*keys, "ingest-e1.pub"))
	persons := []string{"person-a", "person-b", "person-c"}
	devs := map[string]devInfo{}
	sks := map[string]ed25519.PrivateKey{}
	var devIDs []string
	for i := 0; i < *ndev; i++ {
		var s [32]byte
		for j := range s {
			s[j] = byte(rng.Uint32())
		}
		sk := ed25519.NewKeyFromSeed(s[:])
		id := fmt.Sprintf("dev-%02d", i)
		devs[id] = devInfo{Person: persons[i%len(persons)], Pub: base64.StdEncoding.EncodeToString(sk.Public().(ed25519.PublicKey))}
		sks[id] = sk
		devIDs = append(devIDs, id)
	}
	db, _ := json.MarshalIndent(devs, "", " ")
	must(os.WriteFile(filepath.Join(*out, "devices.json"), db, 0o600))
	truth, err := os.Create(filepath.Join(*out, "truth.jsonl"))
	must(err)
	defer truth.Close()
	type content struct {
		sha  []byte
		size int64
	}
	var contents []content
	var total int64
	for i := 0; i < *n; i++ {
		dev := devIDs[rng.IntN(len(devIDs))]
		var rid [16]byte
		for j := range rid {
			rid[j] = byte(rng.Uint32())
		}
		ridHex := hex.EncodeToString(rid[:])
		base := filepath.Join(stg, fmt.Sprintf("%08d-%s", i, ridHex))
		var c content
		var co *ContentObjRef
		if len(contents) > 0 && rng.Float64() < *dup {
			c = contents[rng.IntN(len(contents))]
		} else {
			var size int64
			switch {
			case i == 0:
				size = 0
			case i == 1:
				size = 65536
			case i == 2:
				size = 65537
			default:
				u := rng.Float64()
				switch {
				case u < 0.15:
					size = 20<<10 + rng.Int64N(480<<10)
				case u < 0.85:
					size = 1<<20 + rng.Int64N(7<<20)
				case u < 0.98:
					size = 8<<20 + rng.Int64N(32<<20)
				default:
					size = 50<<20 + rng.Int64N(150<<20)
				}
				size = int64(float64(size) * *scale)
			}
			var cs [32]byte
			for j := range cs {
				cs[j] = byte(rng.Uint32())
			}
			src := io.LimitReader(chachaReader{mrand.NewChaCha8(cs)}, size)
			f, err := os.Create(base + ".obj.age")
			must(err)
			bw := bufio.NewWriterSize(f, 1<<20)
			w, err := age.Encrypt(bw, ingestR...)
			must(err)
			h := sha256.New()
			_, err = io.Copy(io.MultiWriter(w, h), src)
			must(err)
			must(w.Close())
			must(bw.Flush())
			must(f.Close())
			c = content{sha: h.Sum(nil), size: size}
			contents = append(contents, c)
			h0, err := splitHeader(base + ".obj.age")
			must(err)
			co = &ContentObjRef{HeaderMAC: headerMAC(h0)}
			total += size
		}
		body := RecBody{V: 1, Type: "reliquary.file-meta", RecordID: ridHex, DeviceID: dev, Person: devs[dev].Person,
			DedupID: dedupID(fam, c.sha), SHA256: hex.EncodeToString(c.sha), Size: c.size, ContentObject: co,
			Path: "DCIM/Camera", Name: fmt.Sprintf("IMG_%05d.JPG", i), MtimeNs: 1700000000000000000 + int64(i)*1e9}
		line1, _ := json.Marshal(body)
		sig := ed25519.Sign(sks[dev], append([]byte("reliquary-meta-v1\n"), line1...))
		line2, _ := json.Marshal(map[string]string{"alg": "ed25519", "key_id": dev, "sig": base64.StdEncoding.EncodeToString(sig)})
		pt := append(append(append(line1, '\n'), line2...), '\n')
		var mb bytes.Buffer
		w, err := age.Encrypt(&mb, ingestR...)
		must(err)
		w.Write(pt)
		must(w.Close())
		must(os.WriteFile(base+".meta.age", mb.Bytes(), 0o600))
		fmt.Fprintf(truth, "{\"record_id\":%q,\"sha256\":%q,\"size\":%d,\"name\":%q,\"dedup_hit\":%v}\n",
			ridHex, body.SHA256, c.size, body.Name, co == nil)
	}
	fmt.Fprintf(os.Stderr, "gen: %d records, %d unique contents, %d plaintext bytes\n", *n, len(contents), total)
}

// ---------------- ingest ----------------

func parseRecord(pt []byte, devs map[string]devInfo) (RecBody, error) {
	var body RecBody
	parts := bytes.SplitN(pt, []byte("\n"), 3)
	if len(parts) < 3 || len(bytes.TrimRight(parts[2], " ")) != 0 {
		return body, errors.New("bad record framing")
	}
	var sig struct{ Alg, Key_id, Sig string }
	if err := json.Unmarshal(parts[1], &sig); err != nil {
		return body, err
	}
	d, ok := devs[sig.Key_id]
	if !ok || sig.Alg != "ed25519" {
		return body, errors.New("unknown key_id")
	}
	pub, _ := base64.StdEncoding.DecodeString(d.Pub)
	sb, _ := base64.StdEncoding.DecodeString(sig.Sig)
	if !ed25519.Verify(pub, append([]byte("reliquary-meta-v1\n"), parts[0]...), sb) {
		return body, errors.New("bad signature")
	}
	if err := json.Unmarshal(parts[0], &body); err != nil {
		return body, err
	}
	if body.DeviceID != sig.Key_id || body.Person != d.Person {
		return body, errors.New("device/person mismatch")
	}
	return body, nil
}

func loadDevices(store string) map[string]devInfo {
	b, err := os.ReadFile(filepath.Join(store, "devices", "devices.json"))
	must(err)
	m := map[string]devInfo{}
	must(json.Unmarshal(b, &m))
	return m
}

func cmdIngest(args []string) {
	fs := flag.NewFlagSet("ingest", flag.ExitOnError)
	st := fs.String("store", "", "")
	cat := fs.String("catalog", "", "")
	stg := fs.String("staging", "", "")
	ik := fs.String("ingest-key", "", "")
	rc := fs.String("rcpt", "", "file of stored-object recipients (archive [+ recovery])")
	epoch := fs.Int("epoch", 1, "")
	nofsync := fs.Bool("nofsync", false, "NEGATIVE CONTROL ONLY")
	limit := fs.Int("limit", 0, "")
	famF := fs.String("family", "", "family-secret.hex (to recompute dedup IDs)")
	fs.Parse(args)
	doFsync = !*nofsync
	must(LockStore(*st))
	ingestID := loadIdentities(*ik)
	rcpts := loadRecipients(*rc)
	famHex, err := os.ReadFile(*famF)
	must(err)
	fam, _ := hex.DecodeString(strings.TrimSpace(string(famHex)))
	s, err := OpenStore(*st)
	must(err)
	tr, q, err := s.Recover()
	must(err)
	if tr+q > 0 {
		fmt.Fprintf(os.Stderr, "recover: removed %d temp, quarantined %d orphans\n", tr, q)
	}
	db, err := OpenCatalog(*cat)
	must(err)
	devs := loadDevices(*st)
	metas, _ := filepath.Glob(filepath.Join(*stg, "*.meta.age"))
	sort.Strings(metas)
	t0 := time.Now()
	var nItems, nNew int
	var nBytes int64
	for _, mp := range metas {
		if *limit > 0 && nItems >= *limit {
			break
		}
		base := strings.TrimSuffix(mp, ".meta.age")
		rid := filepath.Base(base)[9:]
		if catalogHas(db, rid) {
			fmt.Fprintf(os.Stdout, "ACK %s dup\n", rid)
			continue
		}
		raw, err := os.ReadFile(mp)
		must(err)
		ms := sha256.Sum256(raw)
		metaSHA := hex.EncodeToString(ms[:])
		h0m, err := splitHeader(mp)
		must(err)
		r, err := age.Decrypt(bytes.NewReader(raw), ingestID...)
		must(err)
		pt, err := io.ReadAll(r)
		must(err)
		body, err := parseRecord(pt, devs)
		if err != nil {
			fmt.Fprintf(os.Stdout, "REJECT %s %v\n", rid, err)
			continue
		}
		var h0c []byte
		if body.ContentObject != nil {
			op := base + ".obj.age"
			h0c, err = splitHeader(op)
			must(err)
			if headerMAC(h0c) != body.ContentObject.HeaderMAC {
				fmt.Fprintf(os.Stdout, "REJECT %s header_mac\n", rid)
				continue
			}
			if _, ok := s.Blobs[body.SHA256]; !ok {
				f, err := os.Open(op)
				must(err)
				dr, err := age.Decrypt(bufio.NewReaderSize(f, 1<<20), ingestID...)
				must(err)
				h := sha256.New()
				n, err := io.Copy(h, dr)
				must(err)
				sum := h.Sum(nil)
				if hex.EncodeToString(sum) != body.SHA256 || n != body.Size || dedupID(fam, sum) != body.DedupID {
					f.Close()
					fmt.Fprintf(os.Stdout, "REJECT %s content mismatch\n", rid)
					continue
				}
				_, err = s.PutBlob(body.SHA256, n, f, h0c, ingestID[0], rcpts, *epoch)
				f.Close()
				must(err)
				nNew++
				nBytes += n
			}
		} else if b, ok := s.Blobs[body.SHA256]; !ok || b.Size != body.Size {
			fmt.Fprintf(os.Stdout, "PENDING %s content not yet committed\n", rid)
			continue
		}
		mf, err := os.Open(mp)
		must(err)
		rec, _, err := s.ArchiveRecord(rid, metaSHA, mf, h0m, h0c, ingestID[0], rcpts, *epoch)
		mf.Close()
		must(err)
		maybeCrash("manifest-before-catalog")
		bl := s.Blobs[body.SHA256]
		must(catalogCommit(db, &bl, rec, body, false))
		maybeCrash("catalog-before-ack")
		fmt.Fprintf(os.Stdout, "ACK %s\n", rid)
		maybeCrash("after-ack")
		nItems++
	}
	el := time.Since(t0).Seconds()
	fmt.Fprintf(os.Stderr, "ingest: %d records committed, %d new blobs, %d plaintext bytes in %.2fs (%.1f MB/s)\n",
		nItems, nNew, nBytes, el, float64(nBytes)/1e6/el)
}

// ---------------- recover ----------------

func cmdRecover(args []string) {
	fs := flag.NewFlagSet("recover", flag.ExitOnError)
	st := fs.String("store", "", "")
	cat := fs.String("catalog", "", "")
	fs.Parse(args)
	must(LockStore(*st))
	cut, err := repairManifest(filepath.Join(*st, "manifest", "manifest.jsonl"))
	must(err)
	s, err := OpenStore(*st)
	must(err)
	tr, q, err := s.Recover()
	must(err)
	db, err := OpenCatalog(*cat)
	must(err)
	rows, err := db.Query(`SELECT record_id, sha256 FROM records`)
	must(err)
	viol := 0
	inCat := map[string]bool{}
	for rows.Next() {
		var rid, sha string
		rows.Scan(&rid, &sha)
		inCat[rid] = true
		if _, ok := s.Records[rid]; !ok {
			viol++
		}
		if _, ok := s.Blobs[sha]; !ok {
			viol++
		}
	}
	rows.Close()
	notInCat := 0
	for rid := range s.Records {
		if !inCat[rid] {
			notInCat++
		}
	}
	fmt.Printf("{\"torn_manifest_bytes\":%d,\"tmp_removed\":%d,\"quarantined\":%d,\"catalog_rows_without_store\":%d,\"manifest_records_not_in_catalog\":%d}\n",
		cut, tr, q, viol, notInCat)
}

// ---------------- audit (keyless) ----------------

func sha256File(p string) (string, int64, error) {
	f, err := os.Open(p)
	if err != nil {
		return "", 0, err
	}
	defer f.Close()
	h := sha256.New()
	n, err := io.Copy(h, bufio.NewReaderSize(f, 1<<20))
	return hex.EncodeToString(h.Sum(nil)), n, err
}

func cmdAudit(args []string) {
	fs := flag.NewFlagSet("audit", flag.ExitOnError)
	st := fs.String("store", "", "")
	fs.Parse(args)
	s, err := OpenStore(*st)
	must(err)
	t0 := time.Now()
	var ok, bad, missing int
	var bytesRead int64
	var badList []string
	check := func(p, want string, wantSize int64) {
		got, n, err := sha256File(p)
		bytesRead += n
		switch {
		case err != nil:
			missing++
			badList = append(badList, "missing "+p)
		case got != want || n != wantSize:
			bad++
			badList = append(badList, "mismatch "+p)
		default:
			ok++
		}
	}
	for sha, l := range s.Blobs {
		check(s.BlobPath(sha), l.StoredSHA256, l.StoredSize)
	}
	for rid, l := range s.Records {
		check(s.RecordPath(rid), l.StoredSHA256, l.StoredSize)
	}
	el := time.Since(t0).Seconds()
	res := map[string]any{"objects_ok": ok, "mismatch": bad, "missing": missing, "bytes_read": bytesRead,
		"seconds": el, "MBps": float64(bytesRead) / 1e6 / el, "problems": badList}
	b, _ := json.Marshal(res)
	fmt.Println(string(b))
	if bad+missing > 0 {
		os.Exit(2)
	}
}

// ---------------- rebuild (needs the archive key: attended) ----------------

func decryptAll(p string, ids []age.Identity) ([]byte, error) {
	f, err := os.Open(p)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r, err := age.Decrypt(bufio.NewReader(f), ids...)
	if err != nil {
		return nil, err
	}
	return io.ReadAll(r)
}

// originalBytesSHA reconstructs the device-uploaded file as h0 || stored payload and hashes it.
func originalBytesSHA(stored string, h0 []byte) (string, error) {
	sh, err := splitHeader(stored)
	if err != nil {
		return "", err
	}
	f, err := os.Open(stored)
	if err != nil {
		return "", err
	}
	defer f.Close()
	f.Seek(int64(len(sh)), io.SeekStart)
	h := sha256.New()
	h.Write(h0)
	io.Copy(h, bufio.NewReaderSize(f, 1<<20))
	return hex.EncodeToString(h.Sum(nil)), nil
}

func cmdRebuild(args []string) {
	fs := flag.NewFlagSet("rebuild", flag.ExitOnError)
	st := fs.String("store", "", "")
	out := fs.String("out", "", "")
	ak := fs.String("archive-key", "", "")
	noMan := fs.Bool("no-manifest", false, "rebuild from object files only (manifest ignored)")
	fs.Parse(args)
	ids := loadIdentities(*ak)
	os.Remove(*out)
	db, err := OpenCatalog(*out)
	must(err)
	devs := loadDevices(*st)
	t0 := time.Now()
	s := &Store{Root: *st, Layout: "cas", Blobs: map[string]ManLine{}, Records: map[string]ManLine{}}
	if decl, _ := os.ReadFile(filepath.Join(*st, "REL-STORE-v0")); strings.Contains(string(decl), "layout=ocfl") {
		s.Layout = "ocfl"
	}
	var blobs []ManLine
	var recs []ManLine
	dupLines := 0
	if !*noMan {
		lines, err := readManifest(filepath.Join(*st, "manifest", "manifest.jsonl"))
		must(err)
		// last line wins for a repeated key (same rule as OpenStore); count repeats
		lastB, lastR := map[string]int{}, map[string]int{}
		for _, l := range lines {
			if l.T == "blob" {
				if i, ok := lastB[l.SHA256]; ok {
					blobs[i] = l
					dupLines++
				} else {
					lastB[l.SHA256] = len(blobs)
					blobs = append(blobs, l)
				}
			} else {
				if i, ok := lastR[l.RecordID]; ok {
					recs[i] = l
					dupLines++
				} else {
					lastR[l.RecordID] = len(recs)
					recs = append(recs, l)
				}
			}
		}
	} else {
		// files only: blobs are named by plaintext SHA-256; decrypt to prove it and learn the size
		var paths []string
		if s.Layout == "cas" {
			filepath.WalkDir(filepath.Join(*st, "blobs"), func(p string, d os.DirEntry, e error) error {
				if e == nil && !d.IsDir() {
					paths = append(paths, p)
				}
				return nil
			})
		} else {
			walkOCFLObjects(filepath.Join(*st, "ocfl"), func(objRoot, id string) {
				paths = append(paths, filepath.Join(objRoot, "v1", "content", id+".age"))
			})
		}
		for _, p := range paths {
			sha := strings.TrimSuffix(filepath.Base(p), ".age")
			f, err := os.Open(p)
			must(err)
			r, err := age.Decrypt(bufio.NewReaderSize(f, 1<<20), ids...)
			must(err)
			h := sha256.New()
			n, err := io.Copy(h, r)
			must(err)
			f.Close()
			if hex.EncodeToString(h.Sum(nil)) != sha {
				die("blob %s does not hash to its name", p)
			}
			ss, sz, _ := sha256File(p)
			blobs = append(blobs, ManLine{T: "blob", SHA256: sha, Size: n, StoredSHA256: ss, StoredSize: sz})
		}
		filepath.WalkDir(filepath.Join(*st, "records"), func(p string, d os.DirEntry, e error) error {
			if e == nil && !d.IsDir() {
				ss, sz, _ := sha256File(p)
				recs = append(recs, ManLine{T: "record", RecordID: strings.TrimSuffix(d.Name(), ".age"), StoredSHA256: ss, StoredSize: sz})
			}
			return nil
		})
	}
	for _, b := range blobs {
		_, err := db.Exec(`INSERT OR IGNORE INTO blobs VALUES(?,?,?,?,?,?)`, b.SHA256, b.Size, b.StoredSHA256, b.StoredSize, b.Epoch, b.At)
		must(err)
	}
	metaMismatch := 0
	for _, l := range recs {
		p := s.RecordPath(l.RecordID)
		pt, err := decryptAll(p, ids)
		must(err)
		body, err := parseRecord(pt, devs)
		must(err)
		if !*noMan {
			h0, _ := b64.DecodeString(l.H0)
			got, err := originalBytesSHA(p, h0)
			must(err)
			if got != l.MetaSHA256 {
				metaMismatch++
			}
		}
		must(catalogCommit(db, nil, l, body, false))
	}
	fmt.Fprintf(os.Stderr, "rebuild: %d blobs, %d records in %.2fs; meta_sha256 reconstruction mismatches: %d; repeated manifest keys: %d\n",
		len(blobs), len(recs), time.Since(t0).Seconds(), metaMismatch, dupLines)
}

// ---------------- get (single-file restore by SHA-256) ----------------

func cmdGet(args []string) {
	fs := flag.NewFlagSet("get", flag.ExitOnError)
	st := fs.String("store", "", "")
	ak := fs.String("archive-key", "", "")
	sha := fs.String("sha256", "", "")
	out := fs.String("out", "", "")
	fs.Parse(args)
	t0 := time.Now()
	ids := loadIdentities(*ak)
	s := &Store{Root: *st, Layout: "cas"}
	if decl, _ := os.ReadFile(filepath.Join(*st, "REL-STORE-v0")); strings.Contains(string(decl), "layout=ocfl") {
		s.Layout = "ocfl"
	}
	f, err := os.Open(s.BlobPath(*sha))
	must(err)
	defer f.Close()
	r, err := age.Decrypt(bufio.NewReaderSize(f, 1<<20), ids...)
	must(err)
	o, err := os.Create(*out)
	must(err)
	h := sha256.New()
	n, err := io.Copy(io.MultiWriter(o, h), r)
	must(err)
	must(o.Close())
	okv := hex.EncodeToString(h.Sum(nil)) == *sha
	fmt.Printf("{\"sha256_ok\":%v,\"bytes\":%d,\"seconds\":%.4f}\n", okv, n, time.Since(t0).Seconds())
	if !okv {
		os.Exit(2)
	}
}

// ---------------- verify (A6-S6: A' rewrap round trip) ----------------

func cmdVerify(args []string) {
	fs := flag.NewFlagSet("verify", flag.ExitOnError)
	st := fs.String("store", "", "")
	ak := fs.String("archive-key", "", "")
	rk := fs.String("recovery-key", "", "")
	ik := fs.String("ingest-key", "", "")
	fs.Parse(args)
	s, err := OpenStore(*st)
	must(err)
	arch := loadIdentities(*ak)
	var rec, ing []age.Identity
	if *rk != "" {
		rec = loadIdentities(*rk)
	}
	if *ik != "" {
		ing = loadIdentities(*ik)
	}
	devs := loadDevices(*st)
	c := map[string]int{}
	var hdrStored, hdrOrig []int
	for sha, l := range s.Blobs {
		p := s.BlobPath(sha)
		sh, err := splitHeader(p)
		must(err)
		hdrStored = append(hdrStored, len(sh))
		h0, _ := b64.DecodeString(l.H0)
		hdrOrig = append(hdrOrig, len(h0))
		for name, ids := range map[string][]age.Identity{"archive": arch, "recovery": rec} {
			if ids == nil {
				continue
			}
			pt, err := decryptAll(p, ids)
			sum := sha256.Sum256(pt)
			if err == nil && hex.EncodeToString(sum[:]) == sha && int64(len(pt)) == l.Size {
				c["blob_decrypt_ok_"+name]++
			} else {
				c["blob_decrypt_FAIL_"+name]++
			}
		}
		if ing != nil {
			if _, err := decryptAll(p, ing); err != nil {
				c["blob_ingest_key_refused"]++
			} else {
				c["blob_ingest_key_DECRYPTS_stored"]++
			}
		}
		// provenance: the stored file key must authenticate the original header h0
		fk, err := age.DecryptHeader(sh, arch...)
		must(err)
		if ok, _ := verifyHeaderMAC(h0, fk); ok {
			c["blob_h0_mac_verifies_with_stored_file_key"]++
		} else {
			c["blob_h0_mac_FAIL"]++
		}
		// reconstruct the device's original upload and decrypt it with the ingest key
		if ing != nil {
			f, _ := os.Open(p)
			f.Seek(int64(len(sh)), io.SeekStart)
			r, err := age.Decrypt(io.MultiReader(bytes.NewReader(h0), bufio.NewReader(f)), ing...)
			ok := false
			if err == nil {
				h := sha256.New()
				io.Copy(h, r)
				ok = hex.EncodeToString(h.Sum(nil)) == sha
			}
			f.Close()
			if ok {
				c["blob_original_reconstructed_and_decrypts"]++
			} else {
				c["blob_original_reconstruct_FAIL"]++
			}
		}
	}
	for rid, l := range s.Records {
		p := s.RecordPath(rid)
		pt, err := decryptAll(p, arch)
		must(err)
		body, err := parseRecord(pt, devs)
		if err != nil {
			c["record_sig_FAIL"]++
			continue
		}
		c["record_sig_ok"]++
		h0, _ := b64.DecodeString(l.H0)
		if got, _ := originalBytesSHA(p, h0); got == l.MetaSHA256 {
			c["record_original_bytes_reconstructed_meta_sha256_ok"]++
		} else {
			c["record_meta_sha256_FAIL"]++
		}
		if body.ContentObject != nil {
			ch0, _ := b64.DecodeString(l.ContentH0)
			if headerMAC(ch0) == body.ContentObject.HeaderMAC {
				c["record_content_h0_matches_signed_header_mac"]++
			} else {
				c["record_content_h0_FAIL"]++
			}
		}
	}
	stat := func(v []int) string {
		if len(v) == 0 {
			return "n/a"
		}
		sort.Ints(v)
		return fmt.Sprintf("min %d / max %d bytes", v[0], v[len(v)-1])
	}
	out := map[string]any{"counts": c, "stored_header": stat(hdrStored), "original_header_h0": stat(hdrOrig)}
	b, _ := json.MarshalIndent(out, "", " ")
	fmt.Println(string(b))
}

// ---------------- stage (encrypt a real directory as devices would; bake-off kit) ----------------
// Output stays on the machine that runs it (data class of the source). Prints only counts.

func cmdStage(args []string) {
	fs := flag.NewFlagSet("stage", flag.ExitOnError)
	src := fs.String("src", "", "")
	out := fs.String("out", "", "")
	keys := fs.String("keys", "", "")
	fs.Parse(args)
	stg := filepath.Join(*out, "staging")
	must(os.MkdirAll(stg, 0o700))
	famHex, err := os.ReadFile(filepath.Join(*keys, "family-secret.hex"))
	must(err)
	fam, _ := hex.DecodeString(strings.TrimSpace(string(famHex)))
	ingestR := loadRecipients(filepath.Join(*keys, "ingest-e1.pub"))
	pub, sk, err := ed25519.GenerateKey(nil)
	must(err)
	devs := map[string]devInfo{"dev-00": {Person: "person-a", Pub: base64.StdEncoding.EncodeToString(pub)}}
	db, _ := json.MarshalIndent(devs, "", " ")
	must(os.WriteFile(filepath.Join(*out, "devices.json"), db, 0o600))
	seen := map[string]bool{}
	i, uniq := 0, 0
	var total int64
	err = filepath.WalkDir(*src, func(p string, d os.DirEntry, e error) error {
		if e != nil || !d.Type().IsRegular() {
			return nil
		}
		rid := randHex(16)
		base := filepath.Join(stg, fmt.Sprintf("%08d-%s", i, rid))
		f, err := os.Open(p)
		if err != nil {
			return nil
		}
		h := sha256.New()
		n, err := io.Copy(h, bufio.NewReaderSize(f, 1<<20))
		f.Close()
		if err != nil {
			return nil
		}
		sum := h.Sum(nil)
		shaHex := hex.EncodeToString(sum)
		var co *ContentObjRef
		if !seen[shaHex] {
			seen[shaHex] = true
			uniq++
			total += n
			f, _ := os.Open(p)
			o, err := os.Create(base + ".obj.age")
			must(err)
			bw := bufio.NewWriterSize(o, 1<<20)
			w, err := age.Encrypt(bw, ingestR...)
			must(err)
			_, err = io.Copy(w, bufio.NewReaderSize(f, 1<<20))
			must(err)
			f.Close()
			must(w.Close())
			must(bw.Flush())
			must(o.Close())
			h0, err := splitHeader(base + ".obj.age")
			must(err)
			co = &ContentObjRef{HeaderMAC: headerMAC(h0)}
		}
		rel, _ := filepath.Rel(*src, p)
		body := RecBody{V: 1, Type: "reliquary.file-meta", RecordID: rid, DeviceID: "dev-00", Person: "person-a",
			DedupID: dedupID(fam, sum), SHA256: shaHex, Size: n, ContentObject: co,
			Path: filepath.Dir(rel), Name: d.Name()}
		if st, err := d.Info(); err == nil {
			body.MtimeNs = st.ModTime().UnixNano()
		}
		line1, _ := json.Marshal(body)
		sig := ed25519.Sign(sk, append([]byte("reliquary-meta-v1\n"), line1...))
		line2, _ := json.Marshal(map[string]string{"alg": "ed25519", "key_id": "dev-00", "sig": base64.StdEncoding.EncodeToString(sig)})
		var mb bytes.Buffer
		w, err := age.Encrypt(&mb, ingestR...)
		must(err)
		w.Write(append(append(append(line1, '\n'), line2...), '\n'))
		must(w.Close())
		must(os.WriteFile(base+".meta.age", mb.Bytes(), 0o600))
		i++
		return nil
	})
	must(err)
	fmt.Fprintf(os.Stderr, "stage: %d files, %d unique contents, %d unique plaintext bytes\n", i, uniq, total)
}
