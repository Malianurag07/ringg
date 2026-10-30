# Turns espeak (en-gb) IPA into neutral Indian English pronunciation for Kokoro.
# Deliberately light: retroflex t/d and pure e/o vowels only. No v/w merging,
# no th-stopping and no rolled r, which would make it a caricature.
import re

RULES = [
    (r"tʃ", "ʧ"), (r"dʒ", "ʤ"),        # keep affricates out of the t/d rule
    (r"ɾ", "t"),                       # no American flapped t
    (r"t(?!ʰ)", "ʈ"), (r"d", "ɖ"),     # retroflex t and d
    (r"eɪ", "eː"), (r"əʊ", "oː"), (r"oʊ", "oː"),   # pure vowels
    (r"ᵻ", "ɪ"),
]

# spellings that help the voice say these names clearly
SAY = {"Technocraft's": "Techno-craft's", "Technocraft": "Techno-craft"}

def prepare(text):
    for a, b in SAY.items():
        text = text.replace(a, b)
    return text

def indianize(ipa):
    for a, b in RULES:
        ipa = re.sub(a, b, ipa)
    return ipa
