import json, re, numpy as np, soundfile as sf, sherpa_onnx
W = "/tmp/claude-0/asr/sherpa-onnx-whisper-small.en/"
asr = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=W + "small.en-encoder.int8.onnx", decoder=W + "small.en-decoder.int8.onnx",
                                                 tokens=W + "small.en-tokens.txt", num_threads=4)
a, sr = sf.read("/tmp/claude-0/el/e16k.wav", dtype="float32")
lines = open("/tmp/claude-0/el/sil.txt").read().split("\n")
sil = []  # (start, end) of silences
st = None
for l in lines:
    if l.startswith("start:"): st = float(l.split()[1])
    elif l.startswith("end:") and st is not None: sil.append((st, float(l.split()[1].split("|")[0] if "|" in l else l.split()[1]))); st = None
dur = len(a) / sr
# speech segments between silences
segs, prev = [], 0.0
for s, e in sil:
    if s - prev > 0.05: segs.append((prev, s))
    prev = e
if dur - prev > 0.05: segs.append((prev, dur))
out = []
for s, e in segs:
    x = a[int(s * sr):int(e * sr)]
    if len(x) < 0.15 * sr: continue
    st_ = asr.create_stream(); st_.accept_waveform(sr, x); asr.decode_stream(st_)
    out.append({"s": round(s, 3), "e": round(e, 3), "text": st_.result.text.strip()})
json.dump({"dur": dur, "segs": out, "sil": sil}, open("/tmp/claude-0/el/segs.json", "w"), indent=1)
print(len(out), "segments")
for o in out[:12]: print(o)
print("...")
for o in out[-6:]: print(o)
