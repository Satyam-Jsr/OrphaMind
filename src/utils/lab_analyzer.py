"""
Lab Value Analyzer — Parses free-text lab values, flags abnormal results.
Supports common labs relevant to rare disease workup.
"""
import re
from typing import List, Dict

# Each entry: (name, patterns_list, unit_hint, normal_low, normal_high, critical_low, critical_high)
# Multiple regex patterns per test to handle varied OCR/freetext formats.
# None = no critical threshold defined
LAB_DEFINITIONS = [
    # ── Muscle enzymes ─────────────────────────────────────────────────────────
    ("CK (Creatine Kinase)",
     [r"c\.?k\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:u/l|iu/l|u\.?l)?",
      r"creatine\s*kinase\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"c\.?k\.?\s*\([^)]*\)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "U/L", 30, 200, None, 10000),

    ("CK-MM",
     [r"ck[-\s]?mm\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "U/L", 25, 175, None, None),

    ("LDH",
     [r"l\.?d\.?h\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:u/l|iu/l)?",
      r"lactate\s*dehydrogenase\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "U/L", 120, 246, None, 2500),

    ("Aldolase",
     [r"aldolase\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "U/L", 1.5, 8.1, None, None),

    # ── Liver function ──────────────────────────────────────────────────────────
    ("ALT",
     [r"a\.?l\.?t\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:u/l|iu/l)?",
      r"alanine\s*(?:amino)?transferase\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "U/L", 7, 56, None, 1000),

    ("AST",
     [r"a\.?s\.?t\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:u/l|iu/l)?",
      r"aspartate\s*(?:amino)?transferase\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "U/L", 10, 40, None, 1000),

    ("GGT",
     [r"g\.?g\.?t\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"gamma.?glutamyl\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "U/L", 9, 48, None, None),

    ("Bilirubin Total",
     [r"total\s*bili(?:rubin)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"bili(?:rubin)?\s*(?:total)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mg/dL", 0.2, 1.2, None, 15),

    ("ALP",
     [r"a\.?l\.?p\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"alkaline\s*phosphatase\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "U/L", 44, 147, None, None),

    ("Albumin",
     [r"albumin\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:g/dl)?"],
     "g/dL", 3.5, 5.0, 2.0, None),

    # ── CBC ─────────────────────────────────────────────────────────────────────
    ("Hemoglobin",
     [r"h[gb]b?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:g/dl)?",
      r"hemoglobin\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "g/dL", 12, 17.5, 7, None),

    ("WBC",
     [r"w\.?b\.?c\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:[x×][0-9]+)?",
      r"white\s*blood\s*cell[s]?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "×10³/µL", 4, 11, 2, 30),

    ("Platelets",
     [r"(?:plt|platelets?)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:[x×][0-9]+)?"],
     "×10³/µL", 150, 400, 50, None),

    ("Hematocrit",
     [r"h\.?c\.?t\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"hematocrit\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "%", 36, 52, None, None),

    # ── Metabolic ───────────────────────────────────────────────────────────────
    ("Glucose",
     [r"glucose\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:mg/dl)?",
      r"blood\s*sugar\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mg/dL", 70, 100, 40, 500),

    ("Creatinine",
     [r"creatinine\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:mg/dl)?"],
     "mg/dL", 0.6, 1.2, None, 10),

    ("BUN",
     [r"b\.?u\.?n\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"blood\s*urea\s*nitrogen\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mg/dL", 7, 20, None, 100),

    ("Uric Acid",
     [r"uric\s*acid\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mg/dL", 3.4, 7.0, None, None),

    ("Lactate",
     [r"lactat[e]?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:mmol)?",
      r"lactic\s*acid\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mmol/L", 0.5, 2.2, None, 10),

    ("Ammonia",
     [r"ammonia\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:umol|µmol)?",
      r"nh[34]\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "µmol/L", 11, 32, None, 150),

    ("Sodium",
     [r"sodium\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:meq|mmol)?",
      r"\bna\+?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mEq/L", 135, 145, 120, 160),

    ("Potassium",
     [r"potassium\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:meq|mmol)?",
      r"\bk\+?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mEq/L", 3.5, 5.0, 2.5, 7.0),

    ("Bicarbonate",
     [r"(?:hco3|bicarbonate)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mEq/L", 22, 29, 10, None),

    # ── Thyroid / endocrine ──────────────────────────────────────────────────────
    ("TSH",
     [r"t\.?s\.?h\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:mu/l|miu/l)?"],
     "mIU/L", 0.4, 4.5, None, None),

    ("T4 Free",
     [r"(?:free\s)?t\.?4\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"ft4\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "ng/dL", 0.8, 1.8, None, None),

    # ── Storage / lysosomal / metal markers ─────────────────────────────────────
    ("Ferritin",
     [r"ferritin\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:ng/ml|ug/l)?"],
     "ng/mL", 12, 300, None, None),

    ("Ceruloplasmin",
     [r"ceruloplasmin\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:mg/dl)?"],
     "mg/dL", 20, 60, None, None),

    ("Copper (serum)",
     [r"(?:serum\s)?copper\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:ug/dl|mcg/dl)?"],
     "µg/dL", 70, 140, None, None),

    ("24h Urine Copper",
     [r"(?:24\s*h(?:our)?\s*)?urine\s*copper\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"copper\s*urine\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "µg/24h", 3, 35, None, None),

    ("Alpha-fetoprotein",
     [r"a\.?f\.?p\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:ng/ml)?",
      r"alpha.?feto\w*\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "ng/mL", 0, 8.5, None, None),

    ("Lysosomal Acid Lipase",
     [r"lal\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"lysosomal\s*acid\s*lipase\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "nmol/mL/h", 0.6, 5.0, None, None),

    # ── Inflammation ────────────────────────────────────────────────────────────
    ("CRP",
     [r"c\.?r\.?p\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:mg/l)?",
      r"c.reactive\s*protein\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mg/L", 0, 5, None, None),

    ("ESR",
     [r"e\.?s\.?r\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"erythrocyte\s*sedimentation\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mm/hr", 0, 20, None, None),

    # ── Rare disease specific ───────────────────────────────────────────────────
    ("Sweat Chloride",
     [r"sweat\s*chloride\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:meq/l|mmol)?"],
     "mEq/L", 0, 29, None, None),   # >60 = CF diagnostic

    ("VLCFA (C26:0)",
     [r"vlcfa\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
      r"c26\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "µg/mL", 0, 1.3, None, None),

    ("Phenylalanine",
     [r"phenylalanine\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:mg/dl|umol)?",
      r"\bphe\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"],
     "mg/dL", 0, 1.7, None, None),  # >4 suspicious for PKU
]


def analyze_labs(text: str) -> List[Dict]:
    """
    Parse free-text for lab values, return list of structured results.
    Each result: {name, value, unit, status, fold_change, flag}
    Accepts multiple regex patterns per lab for robustness across OCR outputs.
    """
    text_lower = text.lower()
    results = []

    for name, patterns, unit, low, high, crit_low, crit_high in LAB_DEFINITIONS:
        # patterns is now a list; try each in order, use first match
        match = None
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                break
        if not match:
            continue

        try:
            value = float(match.group(1))
        except (ValueError, IndexError):
            continue

        # Determine status
        status = "NORMAL"
        fold_change = None
        flag = None

        if value < low:
            status = "LOW"
            fold_change = round(value / low, 2) if low > 0 else None
            flag = "⬇ LOW"
        elif value > high:
            status = "HIGH"
            fold_change = round(value / high, 2)
            flag = f"⬆ HIGH ({fold_change:.1f}× ULN)" if fold_change else "⬆ HIGH"

        # Critical override
        if crit_low is not None and value < crit_low:
            status = "CRITICAL LOW"
            flag = "🚨 CRITICAL LOW"
        if crit_high is not None and value > crit_high:
            status = "CRITICAL HIGH"
            flag = f"🚨 CRITICAL HIGH ({round(value/high,1)}× ULN)"

        results.append({
            "name": name,
            "value": value,
            "unit": unit,
            "normal_range": f"{low}–{high}",
            "status": status,
            "fold_change": fold_change,
            "flag": flag if status != "NORMAL" else "✓ Normal",
        })

    return results


def labs_to_clinical_context(labs: List[Dict]) -> str:
    """Convert analyzed labs into a sentence for appending to clinical note."""
    if not labs:
        return ""
    abnormal = [l for l in labs if l["status"] != "NORMAL"]
    if not abnormal:
        return ""
    parts = [f"{l['name']} {l['value']} {l['unit']} ({l['flag']})" for l in abnormal]
    return "Lab findings: " + "; ".join(parts) + "."
