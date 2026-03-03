import json
from pathlib import Path

kb = json.loads(Path('src/data/processed/rare_diseases_knowledge_base.json').read_text(encoding='utf-8'))

# Duchenne entries
matches = [d for d in kb if 'duchenne' in d.get('name','').lower()]
print("=== Duchenne entries ===")
for d in matches:
    print(f"[{d['orpha_id']}] {d['name']} — symptoms: {len(d['symptoms'])}, genes: {len(d['genes'])}")

print()

# Show a disease that HAS symptoms
with_symp = [d for d in kb if d.get('symptoms')]
sample = with_symp[0]
print(f"=== Sample with symptoms: {sample['name']} ===")
print(f"Symptoms: {sample['symptoms'][:8]}")
print(f"Genes: {[g['symbol'] for g in sample['genes'][:5]]}")
print(f"Prevalence: {sample['prevalence']}")

print(f"\nTotal with symptoms: {len(with_symp)}")
print(f"Avg symptoms per disease: {sum(len(d['symptoms']) for d in with_symp) / max(len(with_symp),1):.1f}")
