"""Padding functions for F3-S1.

padme(n): Padme (Nikitin et al., PoPETs 2019) in integer arithmetic, equivalent to
dedis/purb purbs/padding.go paddingLength (E = floor(log2 L), S = floor(log2 E) + 1,
round L up to a multiple of 2^(E-S)); cross-checked against the Go reference.
bucket(n, b): round up to a multiple of b bytes (b = 64 KiB = one age STREAM chunk).
age_ct_len(n, header): age v1 ciphertext length for an n-byte plaintext:
header + 16-byte payload nonce + n + 16 * max(1, ceil(n / 65536)).
"""
import numpy as np

def padme_scalar(n: int) -> int:
    if n < 2:
        return n
    E = n.bit_length() - 1
    S = E.bit_length()          # floor(log2 E) + 1, for E >= 1
    z = E - S
    if z <= 0:
        return n
    m = (1 << z) - 1
    return (n + m) & ~m

def padme(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.uint64)
    out = a.copy()
    big = a >= 2
    x = a[big]
    # floor(log2) via bit length, exact for uint64
    E = np.floor(np.log2(x.astype(np.float64))).astype(np.int64)
    # fix float rounding at exact powers of two / just below
    E = np.where((np.left_shift(np.uint64(1), E.astype(np.uint64)) > x), E - 1, E)
    E = np.where((np.left_shift(np.uint64(1), (E + 1).astype(np.uint64)) <= x), E + 1, E)
    S = np.zeros_like(E)
    nz = E >= 1
    S[nz] = np.floor(np.log2(E[nz].astype(np.float64))).astype(np.int64) + 1
    z = np.maximum(E - S, 0).astype(np.uint64)
    m = np.left_shift(np.uint64(1), z) - np.uint64(1)
    out[big] = (x + m) & ~m
    return out

def bucket(a: np.ndarray, b: int = 65536) -> np.ndarray:
    a = a.astype(np.uint64)
    b = np.uint64(b)
    return ((a + b - np.uint64(1)) // b) * b

def age_ct_len(a: np.ndarray, header: int) -> np.ndarray:
    a = a.astype(np.uint64)
    chunks = np.maximum(np.uint64(1), (a + np.uint64(65535)) // np.uint64(65536))
    return np.uint64(header) + np.uint64(16) + a + np.uint64(16) * chunks
