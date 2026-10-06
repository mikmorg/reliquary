// D2-S1 emulation benchmark (throwaway). Measures how many header unwraps per second
// a plugin-held ingest key can do, ignoring device time:
//   stock   : filippo.io/age plugin client, one plugin process per object (as age v1.3.1 does)
//   batched : one identity-v1 session carrying many headers (file indices 0..B-1), which the
//             C2SP plugin protocol allows ("amortization of identity-specific costs such as a PIN")
// Usage: plugbench -n N -batch B -identity 'AGE-PLUGIN-SWTEST-1...' -native 'AGE-SECRET-KEY-1...'
package main

import (
	"bufio"
	"bytes"
	"encoding/base64"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"time"

	"filippo.io/age"
	"filippo.io/age/plugin"
)

var b64 = base64.RawStdEncoding

type stanza struct {
	typ  string
	args []string
	body []byte
}

func writeStanza(w io.Writer, s stanza) error {
	var b bytes.Buffer
	b.WriteString("-> " + s.typ)
	for _, a := range s.args {
		b.WriteString(" " + a)
	}
	b.WriteString("\n")
	enc := b64.EncodeToString(s.body)
	for len(enc) >= 64 {
		b.WriteString(enc[:64] + "\n")
		enc = enc[64:]
	}
	b.WriteString(enc + "\n")
	_, err := w.Write(b.Bytes())
	return err
}

func readStanza(r *bufio.Reader) (stanza, error) {
	line, err := r.ReadString('\n')
	if err != nil {
		return stanza{}, err
	}
	line = strings.TrimSuffix(line, "\n")
	if !strings.HasPrefix(line, "-> ") {
		return stanza{}, fmt.Errorf("bad stanza line %q", line)
	}
	f := strings.Split(line[3:], " ")
	s := stanza{typ: f[0], args: f[1:]}
	var body strings.Builder
	for {
		l, err := r.ReadString('\n')
		if err != nil {
			return stanza{}, err
		}
		l = strings.TrimSuffix(l, "\n")
		body.WriteString(l)
		if len(l) < 64 {
			break
		}
	}
	s.body, err = b64.DecodeString(body.String())
	return s, err
}

// parseHeaderStanzas extracts recipient stanzas from a canonical age header.
func parseHeaderStanzas(hdr []byte) ([]stanza, error) {
	r := bufio.NewReader(bytes.NewReader(hdr))
	if l, _ := r.ReadString('\n'); l != "age-encryption.org/v1\n" {
		return nil, errors.New("bad intro")
	}
	var out []stanza
	for {
		peek, err := r.Peek(3)
		if err != nil {
			return nil, err
		}
		if string(peek) == "---" {
			return out, nil
		}
		s, err := readStanza(r)
		if err != nil {
			return nil, err
		}
		out = append(out, s)
	}
}

func batchedSession(pluginPath, identity string, headers [][]stanza) (int, error) {
	cmd := exec.Command(pluginPath, "--age-plugin=identity-v1")
	stdin, _ := cmd.StdinPipe()
	stdoutPipe, _ := cmd.StdoutPipe()
	cmd.Stderr = os.Stderr
	if err := cmd.Start(); err != nil {
		return 0, err
	}
	w := bufio.NewWriter(stdin)
	writeStanza(w, stanza{typ: "add-identity", args: []string{identity}})
	for i, ss := range headers {
		for _, s := range ss {
			writeStanza(w, stanza{typ: "recipient-stanza", args: append([]string{fmt.Sprint(i), s.typ}, s.args...), body: s.body})
		}
	}
	writeStanza(w, stanza{typ: "done"})
	w.Flush()
	r := bufio.NewReader(stdoutPipe)
	got := 0
	for {
		s, err := readStanza(r)
		if err != nil {
			return got, err
		}
		switch s.typ {
		case "file-key":
			if len(s.body) != 16 {
				return got, errors.New("bad file key")
			}
			got++
			writeStanza(stdin, stanza{typ: "ok"})
		case "done":
			stdin.Close()
			return got, cmd.Wait()
		case "msg":
			fmt.Fprintf(os.Stderr, "plugin msg: %s\n", s.body)
			writeStanza(stdin, stanza{typ: "ok"})
		case "request-secret", "request-public":
			pin := os.Getenv("PLUGBENCH_PIN")
			if pin == "" {
				writeStanza(stdin, stanza{typ: "fail"})
			} else {
				writeStanza(stdin, stanza{typ: "ok", body: []byte(pin)})
			}
		case "confirm":
			writeStanza(stdin, stanza{typ: "fail"})
		case "error":
			return got, fmt.Errorf("plugin error: %v %s", s.args, s.body)
		default:
			writeStanza(stdin, stanza{typ: "unsupported"})
		}
	}
}

func main() {
	n := flag.Int("n", 500, "objects")
	batch := flag.Int("batch", 100, "headers per batched session")
	pid := flag.String("identity", "", "plugin identity string")
	native := flag.String("native", "", "native identity (for building objects)")
	pluginPath := flag.String("plugin", "age-plugin-swtest", "plugin binary")
	dir := flag.String("dir", "", "read existing age objects from DIR instead of generating (first N files)")
	skipStock := flag.Bool("skip-stock", false, "skip the stock one-process-per-object pass")
	printID := flag.Bool("print-identity", false, "print the swtest plugin identity for -native and exit")
	flag.Parse()
	if *printID {
		fmt.Println(plugin.EncodeIdentity("swtest", []byte(*native)))
		return
	}
	var nid *age.X25519Identity
	var err error
	if *native != "" {
		if nid, err = age.ParseX25519Identity(*native); err != nil {
			panic(err)
		}
	}
	var hdrs [][]byte
	var parsed [][]stanza
	var files []string
	if *dir != "" {
		ents, err := os.ReadDir(*dir)
		if err != nil {
			panic(err)
		}
		for _, e := range ents {
			if len(files) < *n && e.Type().IsRegular() {
				files = append(files, *dir+"/"+e.Name())
			}
		}
		*n = len(files)
	}
	for i := 0; i < *n; i++ {
		var obj []byte
		if *dir != "" {
			obj, err = os.ReadFile(files[i])
			if err != nil {
				panic(err)
			}
		} else {
			var buf bytes.Buffer
			wc, _ := age.Encrypt(&buf, nid.Recipient())
			wc.Write([]byte("x"))
			wc.Close()
			obj = buf.Bytes()
		}
		h, err := age.ExtractHeader(bytes.NewReader(obj))
		if err != nil {
			panic(err)
		}
		hdrs = append(hdrs, h)
		ps, err := parseHeaderStanzas(h)
		if err != nil {
			panic(err)
		}
		parsed = append(parsed, ps)
	}
	ui := &plugin.ClientUI{
		DisplayMessage: func(name, m string) error { return nil },
		RequestValue: func(name, p string, s bool) (string, error) {
			if pin := os.Getenv("PLUGBENCH_PIN"); pin != "" {
				return pin, nil
			}
			return "", errors.New("no ui")
		},
		Confirm:        func(name, p, y, no string) (bool, error) { return false, errors.New("no ui") },
		WaitTimer:      func(name string) {},
	}
	if *pid == "" && *native != "" {
		*pid = plugin.EncodeIdentity("swtest", []byte(*native))
	}
	pi, err := plugin.NewIdentity(*pid, ui)
	if err != nil {
		panic(err)
	}
	res := map[string]any{"n": *n, "batch": *batch}
	var t0 time.Time
	var el float64
	if !*skipStock {
		t0 = time.Now()
		for _, h := range hdrs {
			if _, err := age.DecryptHeader(h, pi); err != nil {
				panic(err)
			}
		}
		el = time.Since(t0).Seconds()
		res["stock_client_elapsed_s"] = el
		res["stock_client_unwraps_per_s"] = float64(*n) / el
	}
	t0 = time.Now()
	total := 0
	for i := 0; i < *n; i += *batch {
		j := i + *batch
		if j > *n {
			j = *n
		}
		got, err := batchedSession(*pluginPath, *pid, parsed[i:j])
		if err != nil {
			panic(err)
		}
		total += got
	}
	el = time.Since(t0).Seconds()
	res["batched_file_keys"] = total
	res["batched_elapsed_s"] = el
	res["batched_unwraps_per_s"] = float64(total) / el
	if nid != nil {
		t0 = time.Now()
		for _, h := range hdrs {
			if _, err := age.DecryptHeader(h, nid); err != nil {
				panic(err)
			}
		}
		el = time.Since(t0).Seconds()
		res["native_inprocess_unwraps_per_s"] = float64(*n) / el
	}
	b, _ := os.ReadFile("/proc/loadavg")
	res["loadavg"] = strings.TrimSpace(string(b))
	res["delay_ms_env"] = os.Getenv("SWTEST_DELAY_MS")
	res["plugin"] = *pluginPath
	json.NewEncoder(os.Stdout).Encode(res)
}
