import json, re, difflib, sys
sys.path.insert(0, "/home/user/ringg/ring_flow")
from script import SCRIPT
NUM = {"1": "one", "2": "two", "7": "seven", "12": "twelve", "89": "eighty nine", "0": "zero"}
def W(s):
    s = s.lower().replace("-", " ").replace("v7ai", "v7 ai")
    s = re.sub(r"(\d+)", lambda m: " " + NUM.get(m[1], m[1]) + " ", s)
    return re.findall(r"[a-z']+", s)
G = json.load(open("/tmp/claude-0/el/segs.json"))
hw, ht = [], []           # transcript words + estimated times
for g in G["segs"]:
    ws = W(g["text"])
    for i, w in enumerate(ws):
        hw.append(w); ht.append(g["s"] + (g["e"] - g["s"]) * i / max(1, len(ws)))
sw, sid = [], []          # script words + (scene, sentence)
for si, (_, ss) in enumerate(SCRIPT):
    for k, s in enumerate(ss):
        for w in W(s): sw.append(w); sid.append((si, k))
sm = difflib.SequenceMatcher(a=sw, b=hw, autojunk=False)
m = {}
for b in sm.get_matching_blocks():
    for j in range(b.size): m[b.a + j] = b.b + j
print("script words", len(sw), "matched", len(m), f"({100*len(m)/len(sw):.1f}%)")
starts, low = {}, []
for key in dict.fromkeys(sid):
    idx = [i for i, x in enumerate(sid) if x == key]
    hit = [i for i in idx if i in m]
    if len(hit) / len(idx) < 0.8: low.append((key, round(len(hit) / len(idx), 2), " ".join(sw[i] for i in idx)))
    first = hit[0]
    # snap to the start of the transcript segment containing that word when it is the segment's first word
    starts[key] = ht[m[first]] - (first - idx[0]) * 0.33
json.dump({f"{a},{b}": t for (a, b), t in starts.items()}, open("/tmp/claude-0/el/starts.json", "w"), indent=0)
print("sentences under 80% matched:", low if low else "none")
for si in range(len(SCRIPT)): print(si, round(starts[(si, 0)], 2), end=" | ")
print()
