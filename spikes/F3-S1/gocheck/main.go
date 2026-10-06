// Cross-check: paddingLength/zeroBytesNeeded copied verbatim from
// dedis/purb purbs/padding.go (master, fetched 2026-09-29), minus the kyber import.
package main

import (
	"bufio"
	"fmt"
	"math"
	"os"
	"strconv"
)

func paddingLength(msgLen uint64) int {
	var mask, paddingNeeded, paddedMsgLen uint64
	zeroBytes := zeroBytesNeeded(msgLen)
	mask = (1 << zeroBytes) - 1
	paddedMsgLen = (msgLen + mask) & ^mask
	paddingNeeded = paddedMsgLen - msgLen
	return int(paddingNeeded)
}

func zeroBytesNeeded(l uint64) uint64 {
	if l == 1 {
		return uint64(0)
	}
	E := math.Floor(math.Log2(float64(l)))
	S := math.Floor(math.Log2(E)) + 1
	return uint64(E - S)
}

func main() {
	sc := bufio.NewScanner(os.Stdin)
	w := bufio.NewWriter(os.Stdout)
	defer w.Flush()
	for sc.Scan() {
		n, _ := strconv.ParseUint(sc.Text(), 10, 64)
		fmt.Fprintf(w, "%d\n", n+uint64(paddingLength(n)))
	}
}
