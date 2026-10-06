// THROWAWAY SPIKE CODE (Reliquary A6-S1 posture probe). Not production code.
//
// retrofit: measure the cost of adding a recipient to an existing store of age v1
// objects LATER (posture A or A'), two ways:
//
//	retrofit rewrap    -in DIR -out DIR -id KEYFILE -rcpt RCPTFILE   header-only rewrap, payload bytes copied
//	retrofit reencrypt -in DIR -out DIR -id KEYFILE -rcpt RCPTFILE   decrypt + encrypt under a fresh file key
//	retrofit check     -dir DIR -id KEYFILE [-orig DIR]              decrypt all; plaintext SHA-256 must equal the
//	                                                                  file name; with -orig, count byte-identical payloads
//
// Every output file is written as temp + fsync + rename + dir fsync, like a6cas.
// Header code follows the C2SP age spec (same approach as a6cas store.go).
package main

import (
	"bufio"
	"bytes"
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
	"os"
	"path/filepath"
	"strings"
	"time"

	"filippo.io/age"
)

var b64 = base64.RawStdEncoding

func must(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, "retrofit:", err)
		os.Exit(1)
	}
}

func ids(p string) []age.Identity {
	f, err := os.Open(p)
	must(err)
	defer f.Close()
	r, err := age.ParseIdentities(f)
	must(err)
	return r
}

func rcpts(p string) []age.Recipient {
	f, err := os.Open(p)
	must(err)
	defer f.Close()
	r, err := age.ParseRecipients(f)
	must(err)
	return r
}

func header(path string) ([]byte, error) {
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
		return nil, errors.New("non-canonical header")
	}
	return raw, nil
}

func stanza(w *bytes.Buffer, st *age.Stanza) {
	w.WriteString("-> " + st.Type)
	for _, a := range st.Args {
		w.WriteString(" " + a)
	}
	w.WriteString("\n")
	enc := b64.EncodeToString(st.Body)
	for len(enc) >= 64 {
		w.WriteString(enc[:64] + "\n")
		enc = enc[64:]
	}
	w.WriteString(enc + "\n")
}

func buildHeader(fk []byte, rs []age.Recipient) ([]byte, error) {
	var buf bytes.Buffer
	buf.WriteString("age-encryption.org/v1\n")
	for _, r := range rs {
		sts, err := r.Wrap(fk)
		if err != nil {
			return nil, err
		}
		for _, st := range sts {
			stanza(&buf, st)
		}
	}
	buf.WriteString("---")
	k, err := hkdf.Key(sha256.New, fk, nil, "header", 32)
	if err != nil {
		return nil, err
	}
	m := hmac.New(sha256.New, k)
	m.Write(buf.Bytes())
	buf.WriteString(" " + b64.EncodeToString(m.Sum(nil)) + "\n")
	return buf.Bytes(), nil
}

func durable(final string, write func(io.Writer) error) (int64, error) {
	tmp := final + ".part"
	f, err := os.OpenFile(tmp, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		return 0, err
	}
	cw := &counter{w: bufio.NewWriterSize(f, 1<<20)}
	if err := write(cw); err != nil {
		f.Close()
		return 0, err
	}
	if err := cw.w.(*bufio.Writer).Flush(); err != nil {
		return 0, err
	}
	if err := f.Sync(); err != nil {
		return 0, err
	}
	f.Close()
	if err := os.Rename(tmp, final); err != nil {
		return 0, err
	}
	d, err := os.Open(filepath.Dir(final))
	if err != nil {
		return 0, err
	}
	defer d.Close()
	return cw.n, d.Sync()
}

type counter struct {
	w io.Writer
	n int64
}

func (c *counter) Write(p []byte) (int, error) { n, err := c.w.Write(p); c.n += int64(n); return n, err }

func list(dir string) []string {
	var out []string
	filepath.Walk(dir, func(p string, fi os.FileInfo, err error) error {
		if err == nil && !fi.IsDir() && strings.HasSuffix(p, ".age") {
			out = append(out, p)
		}
		return nil
	})
	return out
}

func main() {
	mode := os.Args[1]
	fs := flag.NewFlagSet(mode, flag.ExitOnError)
	in := fs.String("in", "", "")
	out := fs.String("out", "", "")
	dir := fs.String("dir", "", "")
	orig := fs.String("orig", "", "")
	idf := fs.String("id", "", "")
	rf := fs.String("rcpt", "", "")
	fs.Parse(os.Args[2:])
	id := ids(*idf)
	t0 := time.Now()
	var nObj, rd, wr int64
	var hdrOld, hdrNew int64
	switch mode {
	case "rewrap", "reencrypt":
		rs := rcpts(*rf)
		must(os.MkdirAll(*out, 0o700))
		for _, p := range list(*in) {
			final := filepath.Join(*out, filepath.Base(p))
			var n int64
			var err error
			if mode == "rewrap" {
				h0, err := header(p)
				must(err)
				fk, err := age.DecryptHeader(h0, id...)
				must(err)
				nh, err := buildHeader(fk, rs)
				must(err)
				for i := range fk {
					fk[i] = 0
				}
				hdrOld += int64(len(h0))
				hdrNew += int64(len(nh))
				src, err := os.Open(p)
				must(err)
				n, err = durable(final, func(w io.Writer) error {
					if _, err := w.Write(nh); err != nil {
						return err
					}
					if _, err := src.Seek(int64(len(h0)), io.SeekStart); err != nil {
						return err
					}
					c, err := io.Copy(w, bufio.NewReaderSize(src, 1<<20))
					rd += c + int64(len(h0))
					return err
				})
				src.Close()
			} else {
				src, err := os.Open(p)
				must(err)
				fi, _ := src.Stat()
				rd += fi.Size()
				n, err = durable(final, func(w io.Writer) error {
					r, err := age.Decrypt(bufio.NewReaderSize(src, 1<<20), id...)
					if err != nil {
						return err
					}
					ew, err := age.Encrypt(w, rs...)
					if err != nil {
						return err
					}
					if _, err := io.Copy(ew, r); err != nil {
						return err
					}
					return ew.Close()
				})
				src.Close()
			}
			must(err)
			wr += n
			nObj++
		}
	case "check":
		var ok, bad, same int64
		for _, p := range list(*dir) {
			f, err := os.Open(p)
			must(err)
			r, err := age.Decrypt(bufio.NewReaderSize(f, 1<<20), id...)
			if err != nil {
				bad++
				f.Close()
				continue
			}
			h := sha256.New()
			c, err := io.Copy(h, r)
			f.Close()
			rd += c
			name := strings.TrimSuffix(filepath.Base(p), ".age")
			if err == nil && hex.EncodeToString(h.Sum(nil)) == name {
				ok++
			} else {
				bad++
			}
			if *orig != "" {
				a, _ := os.ReadFile(p)
				b, _ := os.ReadFile(filepath.Join(*orig, filepath.Base(p)))
				ha, _ := header(p)
				hb, _ := header(filepath.Join(*orig, filepath.Base(p)))
				if bytes.Equal(a[len(ha):], b[len(hb):]) {
					same++
				}
			}
			nObj++
		}
		json.NewEncoder(os.Stdout).Encode(map[string]any{"mode": mode, "objects": nObj, "plaintext_sha256_ok": ok,
			"fail": bad, "payload_byte_identical_to_orig": same, "seconds": time.Since(t0).Seconds()})
		return
	}
	el := time.Since(t0).Seconds()
	json.NewEncoder(os.Stdout).Encode(map[string]any{"mode": mode, "objects": nObj, "bytes_read": rd, "bytes_written": wr,
		"header_bytes_before": hdrOld, "header_bytes_after": hdrNew, "seconds": el, "MBps_written": float64(wr) / 1e6 / el})
}
