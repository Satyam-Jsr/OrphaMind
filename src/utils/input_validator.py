"""
Input Validator — Rejects garbage text, validates clinical note quality.
"""
import re
import math
from typing import Tuple

# Common English medical/general words (lightweight wordlist for ratio check)
_COMMON_WORDS = {
    "the","a","an","is","are","was","were","be","been","being","have","has","had",
    "do","does","did","will","would","could","should","may","might","shall","can",
    "not","no","and","or","but","if","then","than","so","yet","for","with","at",
    "by","from","to","of","in","on","as","up","out","about","into","through",
    "patient","male","female","year","years","old","presents","with","history",
    "progressive","weakness","pain","fever","fatigue","elevated","normal","blood",
    "test","diagnosis","symptoms","clinical","note","exam","physical","lab","result",
    "muscle","nerve","brain","heart","liver","kidney","lung","bone","skin","eye",
    "serum","plasma","urine","hb","ck","ldh","alt","ast","tsh","wbc","rbc","hct",
    "gene","mutation","inherited","autosomal","recessive","dominant","syndrome",
    "disease","disorder","condition","rare","genetic","pediatric","adult","child",
    "mg","dl","ul","mmol","kg","cm","mm","positive","negative","high","low"
}

def _entropy(text: str) -> float:
    """Shannon entropy of character distribution — high = random gibberish."""
    if not text:
        return 0.0
    freq = {}
    for c in text.lower():
        freq[c] = freq.get(c, 0) + 1
    n = len(text)
    return -sum((v/n) * math.log2(v/n) for v in freq.values())

def _real_word_ratio(text: str) -> float:
    """Fraction of tokens that are recognizable words (len>=2, mostly alpha)."""
    tokens = re.findall(r"[a-zA-Z]{2,}", text.lower())
    if not tokens:
        return 0.0
    known = sum(1 for t in tokens if t in _COMMON_WORDS or t.isalpha())
    return known / len(tokens)

def _consonant_cluster_ratio(text: str) -> float:
    """Fraction of alpha chars in long consonant runs (spam signal).
    Also checks per-word, so spaced keyboard mashing is caught.
    """
    alpha = re.sub(r"[^a-zA-Z]", "", text.lower())
    if len(alpha) < 5:
        return 0.0
    clusters = re.findall(r"[^aeiou]{5,}", alpha)
    cluster_len = sum(len(c) for c in clusters)
    ratio_overall = cluster_len / len(alpha)

    # Per-word check: fraction of words that have >=4 consecutive consonants
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    if words:
        gibberish_words = sum(1 for w in words if re.search(r"[^aeiou]{4,}", w))
        word_gibberish_ratio = gibberish_words / len(words)
        return max(ratio_overall, word_gibberish_ratio * 0.8)

    return ratio_overall

def validate_clinical_note(text: str) -> Tuple[bool, str]:
    """
    Returns (is_valid: bool, rejection_reason: str).
    Empty string means valid.
    """
    if not text or not text.strip():
        return False, "Input is empty."

    stripped = text.strip()

    # Minimum length
    if len(stripped) < 20:
        return False, "Input too short. Please provide a meaningful clinical note (at least 20 characters)."

    # Too long — sanity cap
    if len(stripped) > 10_000:
        return False, "Input too long (max 10,000 characters)."

    # Must have at least some alphabetic content
    alpha_chars = sum(1 for c in stripped if c.isalpha())
    if alpha_chars / max(len(stripped), 1) < 0.4:
        return False, "Input contains too few alphabetic characters — please enter a clinical note in plain text."

    # Entropy check — very high entropy = pure random garbage
    ent = _entropy(stripped)
    if ent > 4.8 and len(stripped) < 200:
        return False, "Input appears to be random text. Please describe the patient's symptoms and history."

    # Consonant cluster spam (fafhghghghgku-type)
    cc = _consonant_cluster_ratio(stripped)
    if cc > 0.45:
        return False, "Input contains unintelligible character sequences. Please enter a real clinical description."

    # Word ratio — should have enough recognisable words
    ratio = _real_word_ratio(stripped)
    # Short texts need stricter ratio
    if len(stripped) < 100 and ratio < 0.25:
        return False, "Input does not appear to be meaningful clinical text. Please describe symptoms, history, or lab results."

    return True, ""
