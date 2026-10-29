# Generates the voice-over with Kokoro TTS (offline) and writes sentence timings.
# Usage: python make_voice.py <kokoro-v1.0.onnx> <voices-v1.0.bin>
import json, os, random, sys
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
from script import SCRIPT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voice")
VOICE, SPEED, SR = "af_heart", 1.0, 24000
LEAD, TAIL = 0.6, 0.9          # silence before / after each scene

def main():
    k = Kokoro(sys.argv[1], sys.argv[2])
    os.makedirs(OUT, exist_ok=True)
    rnd = random.Random(4)
    timing = []
    for si, (title, sents) in enumerate(SCRIPT):
        parts = [np.zeros(int(LEAD * SR), np.float32)]
        t = LEAD; starts = []
        for i, s in enumerate(sents):
            a, sr = k.create(s, voice=VOICE, speed=SPEED, lang="en-us")
            assert sr == SR
            starts.append(round(t, 3))
            parts.append(a.astype(np.float32)); t += len(a) / SR
            if i < len(sents) - 1:
                # natural, slightly uneven breathing gaps between sentences
                gap = rnd.uniform(0.32, 0.5)
                parts.append(np.zeros(int(gap * SR), np.float32)); t += gap
        parts.append(np.zeros(int(TAIL * SR), np.float32)); t += TAIL
        sf.write(os.path.join(OUT, f"scene{si:02d}.wav"), np.concatenate(parts), SR)
        timing.append({"title": title, "dur": round(t, 3), "starts": starts})
        print(si, title, round(t, 1), flush=True)
    with open(os.path.join(OUT, "timing.json"), "w") as f:
        json.dump(timing, f, indent=1)

if __name__ == "__main__":
    main()
