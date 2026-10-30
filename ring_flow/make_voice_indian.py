# Voice-over in an Indian English female voice: Kokoro "hf_alpha" speaking neutral Indian English pronunciation
# (indian_english.py), checked sentence by sentence with Whisper. Writes voice/sceneNN.wav + voice/timing.json.
# Usage: python make_voice_indian.py <kokoro-v1.0.onnx> <voices-v1.0.bin> <whisper dir>
import difflib, json, os, random, re, sys
import numpy as np, soundfile as sf, sherpa_onnx
from kokoro_onnx import Kokoro
from indian_english import indianize, prepare
from script import SCRIPT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voice")
VOICE, SR = "hf_alpha", 24000
SPEEDS = [1.04, 1.01, 1.07, 0.98]      # Kokoro is deterministic, so retries vary the pace slightly
LEAD, TAIL = 0.35, 0.5
MIN_DUR = {11: 22.0}
NUM = {"0": "zero", "1": "one", "2": "two", "7": "seven", "10": "ten", "12": "twelve", "89": "eighty nine"}

def words(s):
    s = s.lower().replace("-", " ")
    s = re.sub(r"(\d+)", lambda m: " " + NUM.get(m[1], m[1]) + " ", s)
    return re.findall(r"[a-z']+", s)

def wer(ref, hyp):
    r, h = words(ref), words(hyp)
    same = sum(b.size for b in difflib.SequenceMatcher(a=r, b=h).get_matching_blocks())
    return 1 - same / max(1, len(r)) + max(0, len(h) - len(r)) / max(1, len(r))

def main():
    k = Kokoro(sys.argv[1], sys.argv[2]); wdir = sys.argv[3]
    asr = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=wdir + "/small.en-encoder.int8.onnx",
        decoder=wdir + "/small.en-decoder.int8.onnx", tokens=wdir + "/small.en-tokens.txt", num_threads=4)
    def hear(a):
        s = asr.create_stream(); s.accept_waveform(SR, a); asr.decode_stream(s); return s.result.text
    def say(text):
        ph = indianize(k.tokenizer.phonemize(prepare(text), "en-gb"))
        best = None
        for sp in SPEEDS:
            a, sr = k.create(ph, voice=VOICE, speed=sp, is_phonemes=True); assert sr == SR
            e = wer(text, hear(a.astype(np.float32)))
            if best is None or e < best[0]: best = (e, a.astype(np.float32), sp)
            if e == 0: break
        print(f"   {best[0]:.2f} @{best[2]}  {text}", flush=True)
        return best[0], best[1]

    os.makedirs(OUT, exist_ok=True)
    rnd = random.Random(4)
    timing, worst = [], []
    for si, (title, sents) in enumerate(SCRIPT):
        parts = [np.zeros(int(LEAD * SR), np.float32)]; t = LEAD; starts = []
        for i, s in enumerate(sents):
            starts.append(round(t, 3))
            e, a = say(s); worst.append((e, s))
            parts.append(a); t += len(a) / SR
            if i < len(sents) - 1:
                # natural, slightly uneven breathing gaps; a longer pause before "Thank you"
                gap = 1.4 if (si == len(SCRIPT) - 1 and i == len(sents) - 2) else rnd.uniform(0.28, 0.4)
                parts.append(np.zeros(int(gap * SR), np.float32)); t += gap
        tail = max(TAIL, MIN_DUR.get(si, 0) - t)
        parts.append(np.zeros(int(tail * SR), np.float32)); t += tail
        audio = np.concatenate(parts); audio *= 0.89 / max(1e-6, np.abs(audio).max())
        sf.write(os.path.join(OUT, f"scene{si:02d}.wav"), audio, SR)
        timing.append({"title": title, "dur": round(t, 3), "starts": starts})
        print(si, title, round(t, 1), flush=True)
    with open(os.path.join(OUT, "timing.json"), "w") as f: json.dump(timing, f, indent=1)
    print("total", round(sum(x["dur"] for x in timing), 1))
    print("sentences still imperfect:", [(round(e, 2), s) for e, s in sorted(worst, reverse=True) if e > 0][:12])

if __name__ == "__main__":
    main()
