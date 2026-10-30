import json, sys, numpy as np, soundfile as sf
sys.path.insert(0, "/home/user/ringg/ring_flow")
from script import SCRIPT
G = json.load(open("/tmp/claude-0/el/segs.json")); ST = {tuple(map(int, k.split(","))): v for k, v in json.load(open("/tmp/claude-0/el/starts.json")).items()}
a, sr = sf.read("/tmp/claude-0/el/e48k.wav", dtype="float32"); total = len(a) / sr
N = len(SCRIPT)
cuts = [0.0]
for i in range(1, N):
    s = ST[(i, 0)]
    prev_end = max(g["e"] for g in G["segs"] if g["e"] <= s + 0.05)
    cuts.append(round((prev_end + s) / 2, 3))
cuts.append(total)
OUT = "/home/user/ringg/ring_flow/voice/"
timing = []
for i, (title, ss) in enumerate(SCRIPT):
    c0, c1 = cuts[i], cuts[i + 1]
    seg = a[int(c0 * sr):int(c1 * sr)]
    starts = [round(max(0.0, ST[(i, k)] - c0), 3) for k in range(len(ss))]
    sf.write(OUT + f"scene{i:02d}.wav", seg, sr)
    timing.append({"title": title, "dur": round(len(seg) / sr, 3), "starts": starts})
json.dump(timing, open(OUT + "timing.json", "w"), indent=1)
print("total", round(sum(x["dur"] for x in timing), 2))
for i, x in enumerate(timing): print(i, x["dur"], [round(b - a_, 1) for a_, b in zip(x["starts"], x["starts"][1:] + [x["dur"]])])
