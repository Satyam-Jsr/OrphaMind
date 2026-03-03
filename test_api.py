"""Quick API test for OrphaMind"""
import requests
import json

BASE = "http://localhost:8000"

# 1. Health check
health = requests.get(f"{BASE}/health").json()
print("=== Health ===")
print(f"  Status: {health['status']}")
print(f"  RAG: {health['rag_loaded']}")
print(f"  Reasoning: {health['reasoning_loaded']}")
print(f"  Diseases: {health['diseases_loaded']}")

# 2. Diagnose
print("\n=== Diagnose: DMD Case ===")
resp = requests.post(f"{BASE}/diagnose", json={
    "clinical_note": "8-year-old male with progressive muscle weakness, CK 8500, calf pseudohypertrophy, positive Gowers sign",
    "top_k_diseases": 3,
    "include_literature": True
}, timeout=90)

print(f"HTTP {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Processing time: {round(data['processing_time_ms'])} ms")
    print(f"Urgency: {data['urgency']}")
    print("\nTop diagnoses:")
    for d in data["differential_diagnosis"]:
        print(f"  [{d['confidence']}%] {d['disease']}")
        print(f"    {d['reasoning'][:120]}...")
    print("\nRecommended tests:", data["recommended_tests"][:3])
    print("\nLiterature hits:", len(data.get("literature_references") or []))
else:
    print("ERROR:", json.dumps(resp.json(), indent=2)[:500])
