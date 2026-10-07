import sys
n = int(sys.argv[1]); P = bytes(i for i in range(251)) * 16384; out = sys.stdout.buffer; off = 0
while off < n:
    s = off % 251; t = min(len(P) - s, n - off); out.write(P[s:s+t]); off += t
