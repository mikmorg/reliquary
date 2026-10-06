import numpy as np, subprocess, random
from padlib import padme, padme_scalar
rng = random.Random(20260929)
vals = list(range(0, 5000)) + [2**k + d for k in range(1, 50) for d in (-2, -1, 0, 1, 2)]
vals += [rng.randrange(1, 2**40) for _ in range(200000)]
vals += [rng.randrange(1, 2**33) for _ in range(200000)]
vals = [v for v in vals if v >= 1]
ref = subprocess.run(['./gocheck/padme_ref'], input='\n'.join(map(str, vals)) + '\n',
                     capture_output=True, text=True, check=True).stdout.split()
ref = list(map(int, ref))
vec = padme(np.array(vals, dtype=np.uint64)).tolist()
sca = [padme_scalar(v) for v in vals]
bad_v = sum(1 for a, b in zip(ref, vec) if a != b)
bad_s = sum(1 for a, b in zip(ref, sca) if a != b)
print(f'values={len(vals)} mismatches_vs_go: vectorised={bad_v} scalar={bad_s}')
