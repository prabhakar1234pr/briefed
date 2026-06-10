"""Analyze a captured float32 render vs the 24k reference: duration, mid-stream
silence gaps (breaking), and sample-to-sample discontinuities (clicks/static)."""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
cap_path = Path(sys.argv[1])
rate = int(sys.argv[2])

cap = np.fromfile(cap_path, dtype="<f4")
ref = np.frombuffer((HERE / "ref_24k.pcm").read_bytes(), dtype="<i2").astype(np.float32) / 32768
ref_secs = len(ref) / 24000
cap_secs = len(cap) / rate
print(f"capture={cap_path.name} rate={rate} dur={cap_secs:.2f}s (ref {ref_secs:.2f}s) peak={np.abs(cap).max():.3f}")

# Mid-stream gaps: windows of ~30ms that are near-silent, but flanked by audio.
w = int(0.03 * rate)
wins = [cap[i:i+w] for i in range(0, len(cap)-w, w)]
pk = np.array([np.abs(x).max() for x in wins])
active = pk > 0.02
# find silent windows between the first and last active window (real dropouts)
if active.any():
    lo, hi = np.argmax(active), len(active) - np.argmax(active[::-1])
    inner = ~active[lo:hi]
    gaps = int(inner.sum())
    print(f"mid-stream silent 30ms windows (dropouts): {gaps}  (~{gaps*30}ms of breakage)")
else:
    print("no active audio?!")

# Discontinuities: |sample[n]-sample[n-1]| spikes = clicks/static
d = np.abs(np.diff(cap))
clicks = int((d > 0.25).sum())
print(f"sample jumps >0.25 (clicks): {clicks}   max_jump={d.max():.3f}   mean|d|={d.mean():.5f}")
