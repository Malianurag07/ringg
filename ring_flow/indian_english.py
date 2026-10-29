# Turns espeak (en-us) IPA into Indian English pronunciation for Kokoro.
import re

RULES = [
    (r"ɾ", "ʈ"),                       # American flapped t -> t
    (r"tʃ", "ʧ"), (r"dʒ", "ʤ"),        # keep affricates out of the t/d rule
    (r"t(?!ʰ)", "ʈ"), (r"d", "ɖ"),     # retroflex t and d
    (r"θ", "tʰ"), (r"ð", "d"),         # th sounds: dental stops
    (r"[vw]", "ʋ"),                    # one sound for v and w
    (r"ɚ", "əɾ"), (r"ɜː?", "əɾ"), (r"ɝ", "əɾ"),   # pronounced r after vowels
    (r"ɹ", "ɾ"),                       # tapped r
    (r"eɪ", "eː"), (r"oʊ", "oː"),      # pure vowels
    (r"ɐ", "ə"), (r"ᵻ", "ɪ"),
    (r"ɾɾ", "ɾ"),
]

def indianize(ipa):
    for a, b in RULES:
        ipa = re.sub(a, b, ipa)
    return ipa
