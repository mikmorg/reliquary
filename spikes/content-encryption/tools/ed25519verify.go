// Independent Ed25519 verifier (Go standard library) used by run_tests.py to
// check metadata-record and receipt signatures produced by the Rust prototype.
// Usage: ed25519verify <pubkey-b64> <sig-b64> <message-file>  (exit 0 = valid)
package main

import (
	"crypto/ed25519"
	"encoding/base64"
	"os"
)

func main() {
	pk, err1 := base64.StdEncoding.DecodeString(os.Args[1])
	sig, err2 := base64.StdEncoding.DecodeString(os.Args[2])
	msg, err3 := os.ReadFile(os.Args[3])
	if err1 != nil || err2 != nil || err3 != nil || len(pk) != ed25519.PublicKeySize {
		os.Exit(2)
	}
	if !ed25519.Verify(ed25519.PublicKey(pk), msg, sig) {
		os.Exit(1)
	}
}
