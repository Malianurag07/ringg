# Ring orientation cell: flow video

`ring_orientation_flow.mp4` (1920×1080, about 7 min) is an animated walkthrough of the cell with a voice-over:
one-time setup (hardware, calibration, ring types, trigger timing, signal link), the 14 steps every ring goes
through, the background tasks, why the GPU is needed, and who owns what.

- `script.py`: the voice-over text, one entry per scene.
- `make_voice.py`: makes `voice/sceneNN.wav` and `voice/timing.json` with Kokoro TTS (offline).
- `make_voice_vctk.py`: the current voice-over. Indian English female voice (VCTK speaker p248, VITS via sherpa-onnx), every sentence checked with Whisper.
- `make_voice_clone.py`: the same, in a cloned voice (ZipVoice via sherpa-onnx), with every phrase checked by Whisper speech recognition and regenerated if wrong. The reference voice sample is not stored in the repo.
- `render.py`: draws the animation, synced to the sentence timings, and muxes the audio.

To rebuild it:

```bash
pip install kokoro-onnx soundfile pillow imageio-ffmpeg
# model files: github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0)
python make_voice.py kokoro-v1.0.onnx voices-v1.0.bin
python render.py            # all scenes → ring_orientation_flow.mp4
python render.py -1 5:12    # preview still of scene 5 at 12 s → build/
```
