// D2-S2 throwaway spike: add a recovery recipient to existing age v1 objects
// by rewriting only the header (the payload bytes are left untouched).
//
// NOT production code. It uses only the public filippo.io/age v1.3.1 API
// (ExtractHeader, DecryptHeader, Recipient.Wrap) plus its own stanza encoder
// and header-MAC computation, written from the C2SP age spec:
//   MAC key = HKDF-SHA-256(ikm = file key, salt = empty, info = "header")
//   MAC     = HMAC-SHA-256(MAC key, header bytes up to and including "---")
//
// Subcommands:
//   bench  -kind classic|pq -n N -pool P -workers W   in-memory header rewraps
//   file   -in DIR -out DIR -ingest KEYFILE -recipient RECIPIENT   rewrap files on disk
package main

import (
	"bytes"
	"crypto/hkdf"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"filippo.io/age"
)

var b64 = base64.RawStdEncoding

func marshalStanza(w *bytes.Buffer, s *age.Stanza) {
	w.WriteString("-> ")
	w.WriteString(s.Type)
	for _, a := range s.Args {
		w.WriteString(" ")
		w.WriteString(a)
	}
	w.WriteString("\n")
	enc := b64.EncodeToString(s.Body)
	for len(enc) >= 64 {
		w.WriteString(enc[:64])
		w.WriteString("\n")
		enc = enc[64:]
	}
	// Final line is always shorter than 64 columns (possibly empty).
	w.WriteString(enc)
	w.WriteString("\n")
}

// rewrapHeader returns a new header = old stanzas + stanzas for extra, with a fresh MAC.
func rewrapHeader(hdr []byte, ingest age.Identity, extra age.Recipient) ([]byte, error) {
	fileKey, err := age.DecryptHeader(hdr, ingest)
	if err != nil {
		return nil, fmt.Errorf("unwrap: %w", err)
	}
	idx := bytes.LastIndex(hdr, []byte("\n--- "))
	if idx < 0 {
		return nil, errors.New("no MAC line")
	}
	stanzas, err := extra.Wrap(fileKey)
	if err != nil {
		return nil, fmt.Errorf("wrap: %w", err)
	}
	var buf bytes.Buffer
	buf.Grow(len(hdr) + 2048)
	buf.Write(hdr[:idx+1])
	for _, s := range stanzas {
		marshalStanza(&buf, s)
	}
	buf.WriteString("---")
	macKey, err := hkdf.Key(sha256.New, fileKey, nil, "header", 32)
	if err != nil {
		return nil, err
	}
	m := hmac.New(sha256.New, macKey)
	m.Write(buf.Bytes())
	buf.WriteString(" ")
	buf.WriteString(b64.EncodeToString(m.Sum(nil)))
	buf.WriteString("\n")
	return buf.Bytes(), nil
}

type pair struct {
	ingestID  age.Identity
	ingestR   age.Recipient
	recID     age.Identity
	recR      age.Recipient
	kindLabel string
}

func newPair(kind string) (*pair, error) {
	switch kind {
	case "classic":
		a, err := age.GenerateX25519Identity()
		if err != nil {
			return nil, err
		}
		b, err := age.GenerateX25519Identity()
		if err != nil {
			return nil, err
		}
		return &pair{a, a.Recipient(), b, b.Recipient(), "x25519"}, nil
	case "pq":
		a, err := age.GenerateHybridIdentity()
		if err != nil {
			return nil, err
		}
		b, err := age.GenerateHybridIdentity()
		if err != nil {
			return nil, err
		}
		return &pair{a, a.Recipient(), b, b.Recipient(), "mlkem768x25519"}, nil
	}
	return nil, fmt.Errorf("unknown kind %q", kind)
}

func encryptObj(r age.Recipient, plaintext []byte) ([]byte, error) {
	var out bytes.Buffer
	w, err := age.Encrypt(&out, r)
	if err != nil {
		return nil, err
	}
	if _, err := w.Write(plaintext); err != nil {
		return nil, err
	}
	if err := w.Close(); err != nil {
		return nil, err
	}
	return out.Bytes(), nil
}

func decryptAll(obj []byte, id age.Identity) ([]byte, error) {
	r, err := age.Decrypt(bytes.NewReader(obj), id)
	if err != nil {
		return nil, err
	}
	return io.ReadAll(r)
}

type benchResult struct {
	Kind               string  `json:"kind"`
	N                  int     `json:"n_rewraps"`
	Pool               int     `json:"distinct_headers_in_pool"`
	Workers            int     `json:"workers"`
	GOMAXPROCS         int     `json:"gomaxprocs"`
	NumCPU             int     `json:"num_cpu"`
	ElapsedS           float64 `json:"elapsed_s"`
	RatePerS           float64 `json:"rewraps_per_s"`
	UnwrapOnlyN        int     `json:"unwrap_only_n"`
	UnwrapOnlyElapsedS float64 `json:"unwrap_only_elapsed_s"`
	UnwrapOnlyRate     float64 `json:"unwrap_only_per_s"`
	HeaderBefore       int     `json:"header_bytes_before"`
	HeaderAfter        int     `json:"header_bytes_after"`
	Verified           int     `json:"verified_roundtrips"`
	VerifyNote         string  `json:"verify_note"`
	Load1Before        string  `json:"loadavg_before"`
	Load1After         string  `json:"loadavg_after"`
	GoVersion          string  `json:"go_version"`
}

func loadavg() string {
	b, err := os.ReadFile("/proc/loadavg")
	if err != nil {
		return "n/a"
	}
	return strings.TrimSpace(string(b))
}

func runParallel(n, workers int, f func(i int) error) (time.Duration, error) {
	var next int64 = -1
	var firstErr atomic.Value
	var wg sync.WaitGroup
	start := time.Now()
	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				i := int(atomic.AddInt64(&next, 1))
				if i >= n {
					return
				}
				if err := f(i); err != nil {
					firstErr.CompareAndSwap(nil, err)
					return
				}
			}
		}()
	}
	wg.Wait()
	el := time.Since(start)
	if e := firstErr.Load(); e != nil {
		return el, e.(error)
	}
	return el, nil
}

func cmdBench(args []string) error {
	fs := flag.NewFlagSet("bench", flag.ExitOnError)
	kind := fs.String("kind", "classic", "classic|pq")
	n := fs.Int("n", 1000000, "number of header rewraps")
	pool := fs.Int("pool", 1024, "distinct objects in the pool (cycled)")
	workers := fs.Int("workers", runtime.NumCPU(), "parallel workers")
	unwrapN := fs.Int("unwrap-n", 100000, "unwrap-only operations")
	fs.Parse(args)

	p, err := newPair(*kind)
	if err != nil {
		return err
	}
	objs := make([][]byte, *pool)
	hdrs := make([][]byte, *pool)
	pts := make([][]byte, *pool)
	for i := range objs {
		pt := []byte(fmt.Sprintf("synthetic object %d %s", i, strings.Repeat("x", i%97)))
		o, err := encryptObj(p.ingestR, pt)
		if err != nil {
			return err
		}
		h, err := age.ExtractHeader(bytes.NewReader(o))
		if err != nil {
			return err
		}
		if !bytes.HasPrefix(o, h) {
			return errors.New("ExtractHeader output is not a byte prefix of the object")
		}
		objs[i], hdrs[i], pts[i] = o, h, pt
	}

	// Correctness: rewrap every pool object once, then decrypt with the recovery
	// identity alone and with the ingest identity alone; payload bytes must be unchanged.
	verified := 0
	for i := range objs {
		nh, err := rewrapHeader(hdrs[i], p.ingestID, p.recR)
		if err != nil {
			return err
		}
		payload := objs[i][len(hdrs[i]):]
		newObj := append(append([]byte{}, nh...), payload...)
		for _, id := range []age.Identity{p.recID, p.ingestID} {
			got, err := decryptAll(newObj, id)
			if err != nil {
				return fmt.Errorf("verify obj %d: %w", i, err)
			}
			if !bytes.Equal(got, pts[i]) {
				return fmt.Errorf("verify obj %d: plaintext mismatch", i)
			}
		}
		// Tamper check: flipping a byte in the new stanza must break the MAC.
		bad := append([]byte{}, newObj...)
		bad[len(hdrs[i])-60] ^= 1
		if _, err := decryptAll(bad, p.recID); err == nil {
			return fmt.Errorf("tampered header accepted for obj %d", i)
		}
		verified++
	}
	nh0, _ := rewrapHeader(hdrs[0], p.ingestID, p.recR)

	res := benchResult{Kind: *kind, N: *n, Pool: *pool, Workers: *workers,
		GOMAXPROCS: runtime.GOMAXPROCS(0), NumCPU: runtime.NumCPU(),
		HeaderBefore: len(hdrs[0]), HeaderAfter: len(nh0), Verified: verified,
		VerifyNote: "each pool object: rewrapped header + untouched payload decrypts to the original plaintext with the recovery identity alone and with the ingest identity alone (age.Decrypt v1.3.1); a 1-bit flip in the header is rejected",
		GoVersion:  runtime.Version()}
	res.Load1Before = loadavg()

	el, err := runParallel(*n, *workers, func(i int) error {
		_, err := rewrapHeader(hdrs[i%*pool], p.ingestID, p.recR)
		return err
	})
	if err != nil {
		return err
	}
	res.ElapsedS = el.Seconds()
	res.RatePerS = float64(*n) / el.Seconds()

	el2, err := runParallel(*unwrapN, *workers, func(i int) error {
		_, err := age.DecryptHeader(hdrs[i%*pool], p.ingestID)
		return err
	})
	if err != nil {
		return err
	}
	res.UnwrapOnlyN = *unwrapN
	res.UnwrapOnlyElapsedS = el2.Seconds()
	res.UnwrapOnlyRate = float64(*unwrapN) / el2.Seconds()
	res.Load1After = loadavg()
	return json.NewEncoder(os.Stdout).Encode(res)
}

type fileResult struct {
	Files        int     `json:"files"`
	BytesRead    int64   `json:"bytes_read"`
	BytesWritten int64   `json:"bytes_written"`
	HeaderBytesW int64   `json:"header_bytes_written"`
	ElapsedS     float64 `json:"elapsed_s"`
	Load         string  `json:"loadavg_after"`
}

func cmdFile(args []string) error {
	fs := flag.NewFlagSet("file", flag.ExitOnError)
	in := fs.String("in", "", "input dir of age objects")
	out := fs.String("out", "", "output dir")
	ingest := fs.String("ingest", "", "ingest identity file")
	recipient := fs.String("recipient", "", "recipient to add")
	sidecar := fs.Bool("header-only", false, "write only the new header (.hdr sidecar), not the payload")
	fs.Parse(args)
	f, err := os.Open(*ingest)
	if err != nil {
		return err
	}
	ids, err := age.ParseIdentities(f)
	f.Close()
	if err != nil {
		return err
	}
	rs, err := age.ParseRecipients(strings.NewReader(*recipient))
	if err != nil {
		return err
	}
	if len(ids) != 1 || len(rs) != 1 {
		return errors.New("need exactly one identity and one recipient")
	}
	ents, err := os.ReadDir(*in)
	if err != nil {
		return err
	}
	names := []string{}
	for _, e := range ents {
		if e.Type().IsRegular() {
			names = append(names, e.Name())
		}
	}
	sort.Strings(names)
	os.MkdirAll(*out, 0o700)
	var res fileResult
	start := time.Now()
	for _, name := range names {
		obj, err := os.ReadFile(filepath.Join(*in, name))
		if err != nil {
			return err
		}
		h, err := age.ExtractHeader(bytes.NewReader(obj))
		if err != nil {
			return err
		}
		if !bytes.HasPrefix(obj, h) {
			return fmt.Errorf("%s: non-canonical header", name)
		}
		nh, err := rewrapHeader(h, ids[0], rs[0])
		if err != nil {
			return fmt.Errorf("%s: %w", name, err)
		}
		var data []byte
		dst := filepath.Join(*out, name)
		if *sidecar {
			data = nh
			dst += ".hdr"
		} else {
			data = append(nh, obj[len(h):]...)
		}
		if err := os.WriteFile(dst, data, 0o600); err != nil {
			return err
		}
		res.Files++
		res.BytesRead += int64(len(obj))
		res.BytesWritten += int64(len(data))
		res.HeaderBytesW += int64(len(nh))
	}
	res.ElapsedS = time.Since(start).Seconds()
	res.Load = loadavg()
	return json.NewEncoder(os.Stdout).Encode(res)
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: rewrap bench|file ...")
		os.Exit(2)
	}
	var err error
	switch os.Args[1] {
	case "bench":
		err = cmdBench(os.Args[2:])
	case "file":
		err = cmdFile(os.Args[2:])
	default:
		err = fmt.Errorf("unknown subcommand %q", os.Args[1])
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}
