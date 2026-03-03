"""
Gemini Diagnostic Reasoning Engine
Core intelligence system for OrphaMind
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import logging
from dotenv import load_dotenv

from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"


class DiseaseIndex:
    """Inverted index for O(1) symptom and gene lookups"""

    def __init__(self, knowledge_base: List[Dict]):
        self.diseases: Dict[str, Dict] = {}
        self.symptom_index: Dict[str, set] = {}
        self.gene_index: Dict[str, set] = {}
        self._build(knowledge_base)
        logger.info(
            f"✓ Inverted index: {len(self.symptom_index)} symptom terms, "
            f"{len(self.gene_index)} genes"
        )

    def _build(self, knowledge_base: List[Dict]):
        for disease in knowledge_base:
            oid = disease.get("orpha_id")
            if not oid:
                continue
            self.diseases[oid] = disease
            for symptom in disease.get("symptoms", []):
                key = symptom.lower().strip()
                if key:
                    self.symptom_index.setdefault(key, set()).add(oid)
            for gene in disease.get("genes", []):
                symbol = gene.get("symbol", "").upper()
                if symbol:
                    self.gene_index.setdefault(symbol, set()).add(oid)

    def match(self, symptoms: List[str], genes: Optional[List[str]] = None, top_k: int = 10) -> List[Dict]:
        """Match symptoms/genes against index — O(k) instead of O(n*m)"""
        scores: Dict[str, float] = {}

        for sym in symptoms:
            key = sym.lower().strip()
            for oid in self.symptom_index.get(key, set()):
                scores[oid] = scores.get(oid, 0) + 1.0

        for gene in (genes or []):
            g_upper = gene.upper()
            for oid in self.gene_index.get(g_upper, set()):
                scores[oid] = scores.get(oid, 0) + 3.0

        if not scores:
            return []

        max_score = max(scores.values())
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for oid, score in ranked:
            d = self.diseases.get(oid, {})
            results.append({
                "disease": d.get("name", "Unknown"),
                "orpha_id": oid,
                "score": score / max_score,
                "symptoms": d.get("symptoms", [])[:10],
                "prevalence": d.get("prevalence", {}),
            })
        return results

    def verify_disease_exists(self, disease_name: str) -> Dict:
        """
        ANTI-HALLUCINATION LAYER 1:
        Verify a Gemini-suggested disease name against the Orphanet DB.
        Returns verification status, official name, and Orpha ID.
        """
        name_lower = disease_name.lower().strip()
        # Exact match
        for oid, disease in self.diseases.items():
            if disease.get("name", "").lower() == name_lower:
                return {"verified": True, "orpha_id": oid,
                        "official_name": disease["name"], "match_type": "exact"}
        # Partial match (one name contains the other)
        for oid, disease in self.diseases.items():
            db_name = disease.get("name", "").lower()
            if name_lower in db_name or db_name in name_lower:
                return {"verified": True, "orpha_id": oid,
                        "official_name": disease["name"], "match_type": "partial"}
        return {"verified": False, "orpha_id": None, "official_name": None, "match_type": "none"}


class GeminiReasoningEngine:
    """Gemini-powered diagnostic reasoning engine"""
    
    def __init__(self):
        """Initialize Gemini API"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        self.client = genai.Client(api_key=api_key)
        self.model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")
        # Faster model for lightweight tasks (feature extraction)
        self.fast_model = os.getenv("GEMINI_FAST_MODEL", "models/gemini-2.0-flash")

        # Load knowledge base and build inverted index
        self.knowledge_base = self._load_knowledge_base()
        self.disease_index = DiseaseIndex(self.knowledge_base)

        logger.info("✓ Gemini Reasoning Engine initialized")
        logger.info(f"✓ Loaded {len(self.knowledge_base)} diseases")
    
    def _load_knowledge_base(self) -> List[Dict]:
        """Load structured disease knowledge base"""
        kb_file = PROCESSED_DIR / "rare_diseases_knowledge_base.json"
        
        if not kb_file.exists():
            logger.warning(f"Knowledge base not found: {kb_file}")
            logger.info("Run parse_orphanet.py first")
            return []
        
        with open(kb_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_features(self, clinical_note: str) -> Dict:
        """
        Extract structured features from clinical text using Gemini
        
        Args:
            clinical_note: Unstructured clinical text
            
        Returns:
            Structured features (symptoms, labs, demographics)
        """
        prompt = f"""You are a specialist rare disease clinician. Extract structured clinical features from the note below.

Clinical Note:
{clinical_note}

Rules:
- List symptoms using standard clinical terms (e.g. "proximal muscle weakness", "hepatosplenomegaly")
- Extract gene symbols if mentioned (e.g. DMD, GBA, ATP7B)
- Identify inheritance pattern clues (X-linked, AR, AD)
- Capture numeric lab values with units
- Note relevant negatives (e.g. "no cognitive impairment")

Return ONLY a valid JSON object:
{{
  "age": <number or null>,
  "sex": "male/female/unknown",
  "symptoms": ["precise clinical terms"],
  "genes": ["GENE1"],
  "labs": {{"CK": {{"value": 8500, "unit": "U/L", "status": "elevated"}}}},
  "onset_pattern": "acute/subacute/chronic/progressive",
  "family_history": "positive/negative/unknown",
  "inheritance_clues": "X-linked/AR/AD/unknown",
  "key_findings": ["pivotal finding1"],
  "relevant_negatives": ["absent feature1"]
}}

Return ONLY valid JSON, no explanations."""

        # Use the faster model for extraction — no extended reasoning needed
        response = self.client.models.generate_content(
            model=self.fast_model,
            contents=prompt
        )

        try:
            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith('```'):
                text = text[text.find('\n')+1:]
                if text.endswith('```'):
                    text = text[:text.rfind('```')]
            features = json.loads(text)
            logger.info("✓ Features extracted by Gemini")
            return features
        except json.JSONDecodeError:
            logger.error("Failed to parse Gemini response as JSON")
            text = response.text
            if '{' in text and '}' in text:
                json_str = text[text.find('{'):text.rfind('}')+1]
                return json.loads(json_str)
            raise
    
    def match_diseases(self, features: Dict, top_k: int = 10) -> List[Dict]:
        """
        Match extracted features against disease database using inverted index (O(1)).
        """
        symptoms = features.get("symptoms", [])
        genes = features.get("genes", [])
        matches = self.disease_index.match(symptoms, genes, top_k * 2)

        # Apply age bonus
        age = features.get("age")
        if age and matches:
            for m in matches:
                d = self.disease_index.diseases.get(m["orpha_id"], {})
                if any(
                    self._age_matches_onset(age, onset)
                    for onset in d.get("age_of_onset", [])
                ):
                    m["score"] = min(1.0, m["score"] + 0.2)
            matches.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"✓ Fast-matched {len(matches[:top_k])} diseases (inverted index)")
        return matches[:top_k]

    def _verify_diagnoses(self, differential: List[Dict]) -> List[Dict]:
        """
        ANTI-HALLUCINATION LAYER 2:
        Cross-check every Gemini-suggested disease against Orphanet.
        Reduces confidence and flags diseases not found in the DB.
        """
        for dx in differential:
            v = self.disease_index.verify_disease_exists(dx.get("disease", ""))
            dx["verified_in_orphanet"] = v["verified"]
            dx["verification_match"] = v["match_type"]
            # Use official name if partial match found
            if v["verified"] and v["match_type"] == "partial":
                dx["disease"] = v["official_name"]
            if not v["verified"]:
                dx["confidence"] = max(10, dx.get("confidence", 50) - 20)
                dx["hallucination_warning"] = (
                    "Disease name not confirmed in Orphanet — verify manually before clinical use"
                )
            else:
                dx["hallucination_warning"] = None
        return differential

    def _check_rag_support(self, differential: List[Dict], rag_results: List[Dict]) -> List[Dict]:
        """
        ANTI-HALLUCINATION LAYER 3:
        Verify each diagnosis has literature support.
        Lowers confidence if a disease has no evidence in retrieved chunks.
        """
        # Build per-chunk lookup: content + source type from metadata
        rag_entries = [
            {
                "text": r.get("content", "").lower(),
                "src_type": (r.get("metadata") or {}).get("type", "unknown")
            }
            for r in rag_results
        ]
        rag_text_all = " ".join(e["text"] for e in rag_entries)

        for dx in differential:
            words = [w for w in dx.get("disease", "").lower().split() if len(w) > 4]

            # Find which chunks matched
            matched = [e for e in rag_entries if any(w in e["text"] for w in words)]
            lit_support = bool(matched)

            # Determine source label from matched chunk types
            if matched:
                types = {e["src_type"] for e in matched}
                if types == {"genereviews"}:
                    lit_label = "GeneReviews literature"
                elif "orphanet" in types and "genereviews" in types:
                    lit_label = "Orphanet + GeneReviews literature"
                elif "orphanet" in types:
                    lit_label = "Orphanet rare disease literature"
                else:
                    lit_label = "rare disease literature"
            else:
                lit_label = None

            dx["literature_supported"] = lit_support
            if not lit_support and not dx.get("verified_in_orphanet"):
                dx["confidence"] = max(5, dx.get("confidence", 50) - 15)
                dx["evidence_source"] = "Gemini training data only — no local evidence found"
            elif lit_support and dx.get("verified_in_orphanet"):
                dx["evidence_source"] = f"Verified: Orphanet DB + {lit_label}"
            elif dx.get("verified_in_orphanet"):
                dx["evidence_source"] = "Verified: Orphanet DB (no matching literature chunk)"
            else:
                dx["evidence_source"] = f"{lit_label} only"
        return differential

    def _add_disclaimer(self, diagnosis: Dict) -> Dict:
        """
        ANTI-HALLUCINATION LAYER 4:
        Always attach a medical disclaimer and data provenance to every response.
        """
        diagnosis["disclaimer"] = (
            "OrphaMind is a diagnostic support tool only. "
            "All diagnoses must be confirmed by a qualified medical professional. "
            "Confidence scores are indicative, not clinically validated probabilities."
        )
        diagnosis["data_sources"] = {
            "structured_db": "Orphanet (11,456 rare diseases)",
            "literature": "Orphanet rare disease literature + GeneReviews (inherited disease chapters)",
            "ai_model": self.model_name,
        }
        return diagnosis

    def diagnose(self, clinical_note: str, rag_system=None, top_k: int = 5) -> Dict:
        """
        Full pipeline: feature extraction → parallel RAG + DB → Gemini reasoning
        → anti-hallucination verification → disclaimer.
        """
        # Step 1: feature extraction
        features = self.extract_features(clinical_note)

        # Steps 2 & 3 in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            db_future = executor.submit(self.match_diseases, features, top_k)
            if rag_system:
                symptoms_str = ", ".join(features.get("symptoms", []))
                rag_future = executor.submit(rag_system.search, symptoms_str, 5)
            else:
                rag_future = None
            structured_matches = db_future.result()
            rag_results = rag_future.result() if rag_future else []

        # Step 4: Gemini reasoning
        diagnosis = self.generate_diagnosis(features, structured_matches, rag_results)

        # Step 5: Anti-hallucination — verify diseases against Orphanet
        differential = self._verify_diagnoses(diagnosis.get("differential_diagnosis", []))
        # Step 6: Anti-hallucination — check literature support
        differential = self._check_rag_support(differential, rag_results)
        diagnosis["differential_diagnosis"] = differential

        # Step 7: Attach disclaimer
        diagnosis = self._add_disclaimer(diagnosis)

        diagnosis["patient_features"] = features
        diagnosis["literature_references"] = rag_results
        return diagnosis
    
    def _age_matches_onset(self, age: int, onset: str) -> bool:
        """Check if age matches onset description"""
        onset_lower = onset.lower()
        if 'neonatal' in onset_lower and age < 1:
            return True
        if 'infancy' in onset_lower and age < 2:
            return True
        if 'childhood' in onset_lower and 2 <= age < 12:
            return True
        if 'adolescent' in onset_lower and 12 <= age < 18:
            return True
        if 'adult' in onset_lower and age >= 18:
            return True
        return False
    
    def generate_diagnosis(
        self,
        features: Dict,
        structured_matches: List[Dict],
        rag_results: List[Dict]
    ) -> Dict:
        """
        Generate differential diagnosis using Gemini reasoning
        
        Args:
            features: Extracted patient features
            structured_matches: Disease database matches
            rag_results: RAG literature results
            
        Returns:
            Differential diagnosis with reasoning
        """
        # Build comprehensive prompt
        prompt = f"""You are a board-certified rare disease diagnostician at a tertiary referral center.
Reason through this case step by step before producing your output.

## STEP 1 — PATIENT SUMMARY
Age: {features.get('age','?')} | Sex: {features.get('sex','unknown')} | Onset: {features.get('onset_pattern','unknown')} | Family Hx: {features.get('family_history','unknown')}
Symptoms: {', '.join(features.get('symptoms', []))}
Key findings: {', '.join(features.get('key_findings', []))}
Relevant negatives: {', '.join(features.get('relevant_negatives', []))}
Inheritance clues: {features.get('inheritance_clues', 'unknown')}

## STEP 2 — DATABASE CANDIDATES (ranked by symptom overlap)
{json.dumps(structured_matches[:8], indent=2)}

## STEP 3 — LITERATURE EVIDENCE
{self._format_literature(rag_results[:6])}

## STEP 4 — REASONING RULES
- Confidence > 80%: requires ≥3 matching features + database hit + literature support
- Confidence 50–80%: ≥2 matching features OR database hit
- Confidence < 50%: single feature match; mark evidence_strength as "weak"
- NEVER invent lab values, gene names, or features not in the data above
- Penalise any disease absent from the database candidates unless literature clearly supports it
- Explicitly note what argues AGAINST each diagnosis
- If the case is ambiguous, say so in the summary

## STEP 5 — OUTPUT
Return ONLY valid JSON — no markdown fences, no preamble:
{{
  "differential_diagnosis": [
    {{
      "disease": "Exact Orphanet official name",
      "confidence": 85,
      "reasoning": "Step-by-step rationale citing specific features and evidence sources",
      "supporting_features": ["feature from data"],
      "against_evidence": ["feature that argues against"],
      "evidence_strength": "strong/moderate/weak",
      "inheritance": "X-linked recessive / AR / AD / unknown"
    }}
  ],
  "recommended_tests": ["specific tier-1 test", "confirmatory test"],
  "urgency": "routine/urgent/emergency",
  "urgency_reason": "why this urgency level",
  "summary": "Paragraph summary with explicit uncertainty acknowledgement"
}}"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )

        try:
            text = response.text.strip()
            if text.startswith('```'):
                text = text[text.find('\n')+1:]
                if text.endswith('```'):
                    text = text[:text.rfind('```')]
            diagnosis = json.loads(text)
            logger.info("✓ Diagnosis generated by Gemini")
            return diagnosis
        except json.JSONDecodeError:
            logger.warning("Could not parse diagnosis as JSON, returning raw text")
            return {
                "raw_diagnosis": response.text,
                "differential_diagnosis": [],
                "error": "JSON parsing failed"
            }
    
    def _format_literature(self, rag_results: List[Dict]) -> str:
        """Format RAG results for prompt"""
        formatted = []
        for i, result in enumerate(rag_results, 1):
            formatted.append(f"{i}. Source: {result['source']}\n   {result['content'][:300]}...")
        return "\n\n".join(formatted)
    
    def explain_diagnosis(self, diagnosis: Dict, for_physician: bool = True) -> str:
        """
        Generate human-readable explanation using Gemini
        
        Args:
            diagnosis: Differential diagnosis output
            for_physician: If True, use medical terminology; if False, patient-friendly
            
        Returns:
            Natural language explanation
        """
        audience = "physician" if for_physician else "patient and family"
        
        prompt = f"""Convert this differential diagnosis into a clear, professional explanation for a {audience}.

Diagnosis Data:
{json.dumps(diagnosis, indent=2)}

Requirements:
- Use appropriate terminology for the audience
- Explain the reasoning clearly
- Highlight key evidence
- Provide next steps
- Be compassionate if for patient

Generate a well-structured explanation."""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text


def main():
    """Test the reasoning engine"""
    logger.info("=== Gemini Reasoning Engine Test ===")
    
    # Initialize
    engine = GeminiReasoningEngine()
    
    # Test case: Duchenne Muscular Dystrophy
    test_note = """
    8-year-old male presents with progressive muscle weakness over the past year.
    Mother reports difficulty climbing stairs and frequent falls. 
    Physical exam shows calf pseudohypertrophy and positive Gowers' sign.
    Lab results: Creatine kinase 8500 U/L (normal: 25-200).
    Family history: No known muscle disorders, but maternal uncle died young of unknown cause.
    """
    
    logger.info("\n=== Test Clinical Note ===")
    print(test_note)
    
    # Extract features
    logger.info("\n=== Extracting Features with Gemini ===")
    features = engine.extract_features(test_note)
    print(json.dumps(features, indent=2))
    
    # Match diseases
    logger.info("\n=== Matching Against Disease Database ===")
    matches = engine.match_diseases(features, top_k=5)
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match['disease']} (Score: {match['score']:.2f})")
    
    # For full diagnosis, would need RAG results here
    logger.info("\n=== Reasoning Engine Ready ===")
    logger.info("To generate full diagnosis, integrate with RAG system")


if __name__ == "__main__":
    main()
