# Voice-over in a cloned voice (ZipVoice via sherpa-onnx), checked phrase by phrase with Whisper.
# Writes voice/sceneNN.wav + voice/timing.json, same format as make_voice.py.
# Usage: python make_voice_clone.py <zipvoice dir> <vocos_24khz.onnx> <lexicon.txt> <whisper dir> <ref.wav> "<ref transcript>"
import difflib, json, os, re, sys
import numpy as np, soundfile as sf, sherpa_onnx
from script import SCRIPT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voice")
SR = 24000
LEAD, TAIL = 0.4, 0.6
MIN_DUR = {11: 22.0}
SPEEDS = [1.2, 1.15, 1.25, 1.1, 1.3, 1.05]
NUM = {"0": "zero", "1": "one", "2": "two", "7": "seven", "10": "ten", "12": "twelve", "89": "eighty nine"}

def words(s):
    s = s.lower().replace("-", " ")
    s = re.sub(r"(\d+)", lambda m: " " + NUM.get(m[1], m[1]) + " ", s)
    return re.findall(r"[a-z']+", s)

def wer(ref, hyp):
    r, h = words(ref), words(hyp)
    sm = difflib.SequenceMatcher(a=r, b=h)
    same = sum(b.size for b in sm.get_matching_blocks())
    return 1 - same / max(1, len(r)) + max(0, len(h) - len(r)) / max(1, len(r))

def chunks(sentence):
    # split at sentence ends and commas, keeping each phrase at least 3 words
    parts = [p.strip() for p in re.split(r"(?<=[.?!,:])\s+", sentence) if p.strip()]
    out = []
    for p in parts:
        if out and (len(out[-1].split()) < 3 or len(p.split()) < 3): out[-1] += " " + p
        else: out.append(p)
    return out

def main():
    zdir, vocoder, lexicon, wdir, ref_path, ref_text = sys.argv[1:7]
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        zipvoice=sherpa_onnx.OfflineTtsZipvoiceModelConfig(tokens=zdir + "/tokens.txt", encoder=zdir + "/encoder.int8.onnx",
            decoder=zdir + "/decoder.int8.onnx", vocoder=vocoder, data_dir=zdir + "/espeak-ng-data", lexicon=lexicon),
        num_threads=4)))
    asr = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=wdir + "/small.en-encoder.int8.onnx",
        decoder=wdir + "/small.en-decoder.int8.onnx", tokens=wdir + "/small.en-tokens.txt", num_threads=4)
    ref, rsr = sf.read(ref_path, dtype="float32"); ref = ref.tolist()

    def hear(a):
        s = asr.create_stream(); s.accept_waveform(SR, a); asr.decode_stream(s); return s.result.text

    def say(text):
        best = None
        for sp in SPEEDS:
            g = tts.generate(text, ref_text, ref, rsr, sp, 4)
            a = np.array(g.samples, np.float32)
            # trim generated leading/trailing silence
            nz = np.where(np.abs(a) > 0.01)[0]
            if len(nz): a = a[max(0, nz[0] - 600): nz[-1] + 1200]
            e = wer(text, hear(a))
            if best is None or e < best[0]: best = (e, a, sp)
            if e == 0: break
        print(f"   {best[0]:.2f} @{best[2]}  {text}", flush=True)
        return best[1], best[0]

    os.makedirs(OUT, exist_ok=True)
    timing, worst = [], []
    for si, (title, sents) in enumerate(SCRIPT):
        parts = [np.zeros(int(LEAD * SR), np.float32)]; t = LEAD; starts = []
        for i, s in enumerate(sents):
            starts.append(round(t, 3))
            for j, c in enumerate(chunks(s)):
                a, e = say(c); worst.append((e, c))
                parts.append(a); t += len(a) / SR
                if j < len(chunks(s)) - 1:
                    parts.append(np.zeros(int(0.14 * SR), np.float32)); t += 0.14
            if i < len(sents) - 1:
                gap = 1.4 if (si == len(SCRIPT) - 1 and i == len(sents) - 2) else 0.34   # pause before "Thank you"
                parts.append(np.zeros(int(gap * SR), np.float32)); t += gap
        tail = max(TAIL, MIN_DUR.get(si, 0) - t)
        parts.append(np.zeros(int(tail * SR), np.float32)); t += tail
        audio = np.concatenate(parts); audio *= 0.89 / max(1e-6, np.abs(audio).max())
        sf.write(os.path.join(OUT, f"scene{si:02d}.wav"), audio, SR)
        timing.append({"title": title, "dur": round(t, 3), "starts": starts})
        print(si, title, round(t, 1), flush=True)
    with open(os.path.join(OUT, "timing.json"), "w") as f: json.dump(timing, f, indent=1)
    print("total", round(sum(x["dur"] for x in timing), 1))
    print("phrases still imperfect:", [(round(e, 2), c) for e, c in sorted(worst, reverse=True) if e > 0][:15])

if __name__ == "__main__":
    main()
