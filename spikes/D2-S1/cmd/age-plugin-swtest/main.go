// Throwaway software stand-in for a hardware-key age plugin (D2-S1 emulation).
// The plugin identity's data is a native "AGE-SECRET-KEY-1..." string; the plugin
// unwraps native X25519 stanzas with it. It adds NO hardware latency: it shows only
// the plugin-protocol and process overhead that a YubiKey/TPM plugin pays on top of
// its own device time. SWTEST_DELAY_MS adds a fixed sleep per unwrap to model device
// latency. NOT production code.
package main

import (
	"os"
	"strconv"
	"time"

	"filippo.io/age"
	"filippo.io/age/plugin"
)

type delayed struct {
	id    age.Identity
	delay time.Duration
}

func (d delayed) Unwrap(s []*age.Stanza) ([]byte, error) {
	if d.delay > 0 {
		time.Sleep(d.delay)
	}
	return d.id.Unwrap(s)
}

func main() {
	p, err := plugin.New("swtest")
	if err != nil {
		panic(err)
	}
	ms, _ := strconv.Atoi(os.Getenv("SWTEST_DELAY_MS"))
	p.HandleIdentity(func(data []byte) (age.Identity, error) {
		id, err := age.ParseX25519Identity(string(data))
		if err != nil {
			return nil, err
		}
		return delayed{id, time.Duration(ms) * time.Millisecond}, nil
	})
	os.Exit(p.Main())
}
