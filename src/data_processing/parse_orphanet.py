"""
Orphanet XML Parser
Converts Orphanet XML data into structured JSON for the knowledge base
"""

import xml.etree.ElementTree as ET
import json
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "datasets"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def parse_orphanet_diseases(xml_path: Path) -> List[Dict]:
    """Parse Orphanet disease list XML"""
    logger.info(f"Parsing {xml_path}...")
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    diseases = []
    
    for disorder in root.findall(".//Disorder"):
        disease = {}
        
        # Basic info
        orpha_id = disorder.find("OrphaCode")
        disease["orpha_id"] = orpha_id.text if orpha_id is not None else None
        
        name = disorder.find("Name")
        disease["name"] = name.text if name is not None else None
        
        # Synonyms
        synonyms = []
        for syn in disorder.findall(".//Synonym"):
            if syn.text:
                synonyms.append(syn.text)
        disease["synonyms"] = synonyms
        
        # Classification
        disease_type = disorder.find(".//DisorderType/Name")
        disease["type"] = disease_type.text if disease_type is not None else None
        
        # Age of onset
        age_of_onset = []
        for age in disorder.findall(".//AverageAgeOfOnset/Name"):
            if age.text:
                age_of_onset.append(age.text)
        disease["age_of_onset"] = age_of_onset
        
        # Inheritance
        inheritance = []
        for inherit in disorder.findall(".//TypeOfInheritance/Name"):
            if inherit.text:
                inheritance.append(inherit.text)
        disease["inheritance"] = inheritance
        
        diseases.append(disease)
    
    logger.info(f"Parsed {len(diseases)} diseases")
    return diseases


def parse_orphanet_clinical_signs(xml_path: Path) -> Dict[str, List]:
    """Parse Orphanet clinical signs XML (HPO terms per disease)"""
    logger.info(f"Parsing {xml_path}...")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    disease_symptoms = {}

    # Structure: HPODisorderSetStatus > Disorder > HPODisorderAssociationList
    #            > HPODisorderAssociation > HPO > HPOTerm
    for disorder in root.findall(".//Disorder"):
        orpha_code = disorder.find("OrphaCode")
        if orpha_code is None:
            continue

        orpha_id = orpha_code.text
        symptoms = []

        for assoc in disorder.findall(".//HPODisorderAssociation"):
            hpo_term = assoc.find("HPO/HPOTerm")
            hpo_id   = assoc.find("HPO/HPOId")
            freq     = assoc.find("HPOFrequency/Name")
            if hpo_term is not None and hpo_term.text:
                symptoms.append({
                    "term":      hpo_term.text,
                    "hpo_id":    hpo_id.text if hpo_id is not None else None,
                    "frequency": freq.text   if freq   is not None else None,
                })

        if symptoms:
            disease_symptoms[orpha_id] = symptoms

    logger.info(f"Parsed symptoms for {len(disease_symptoms)} diseases")
    return disease_symptoms


def parse_orphanet_genes(xml_path: Path) -> Dict[str, List[str]]:
    """Parse Orphanet gene associations XML"""
    logger.info(f"Parsing {xml_path}...")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    disease_genes = {}

    # Structure: DisorderList > Disorder > DisorderGeneAssociationList
    #            > DisorderGeneAssociation > Gene > Symbol
    for disorder in root.findall(".//Disorder"):
        orpha_code = disorder.find("OrphaCode")
        if orpha_code is None:
            continue

        orpha_id = orpha_code.text
        genes = []

        for assoc in disorder.findall(".//DisorderGeneAssociation"):
            symbol = assoc.find("Gene/Symbol")
            name   = assoc.find("Gene/Name")
            if symbol is not None and symbol.text:
                genes.append({
                    "symbol": symbol.text,
                    "name":   name.text if name is not None else None,
                })

        if genes:
            disease_genes[orpha_id] = genes

    logger.info(f"Parsed genes for {len(disease_genes)} diseases")
    return disease_genes


def parse_orphanet_prevalence(xml_path: Path) -> Dict[str, Dict]:
    """Parse Orphanet prevalence data XML"""
    logger.info(f"Parsing {xml_path}...")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    disease_prevalence = {}

    # Structure: DisorderList > Disorder > PrevalenceList > Prevalence
    for disorder in root.findall(".//Disorder"):
        orpha_code = disorder.find("OrphaCode")
        if orpha_code is None:
            continue

        orpha_id = orpha_code.text

        # Take the first point-prevalence entry, fall back to any
        best_prev = None
        for prev in disorder.findall(".//Prevalence"):
            ptype = prev.find("PrevalenceType/Name")
            if ptype is not None and "point" in (ptype.text or "").lower():
                best_prev = prev
                break
        if best_prev is None:
            best_prev = disorder.find(".//Prevalence")

        if best_prev is not None:
            pc = best_prev.find("PrevalenceClass/Name")
            pt = best_prev.find("PrevalenceType/Name")
            geo = best_prev.find("PrevalenceGeographic/Name")
            disease_prevalence[orpha_id] = {
                "class":      pc.text  if pc  is not None else None,
                "type":       pt.text  if pt  is not None else None,
                "geographic": geo.text if geo is not None else None,
            }
    
    logger.info(f"Parsed prevalence for {len(disease_prevalence)} diseases")
    return disease_prevalence


def merge_disease_data(
    diseases: List[Dict],
    symptoms: Dict,
    genes: Dict,
    prevalence: Dict
) -> List[Dict]:
    """Merge all disease data sources"""
    logger.info("Merging disease data...")

    for disease in diseases:
        orpha_id = disease.get("orpha_id")

        # Symptoms: full HPO objects + plain string list for easy matching
        hpo_list = symptoms.get(orpha_id, [])
        disease["hpo_terms"] = hpo_list
        disease["symptoms"]  = [h["term"] for h in hpo_list]  # plain strings

        disease["genes"]      = genes.get(orpha_id, [])
        disease["prevalence"] = prevalence.get(orpha_id, {})

    return diseases


def main():
    """Main parsing workflow"""
    logger.info("=== Orphanet Data Parser ===")
    
    # Check if files exist
    diseases_xml = RAW_DIR / "orphanet_diseases.xml"
    if not diseases_xml.exists():
        logger.error(f"File not found: {diseases_xml}")
        logger.error("Please run download_datasets.py first")
        return
    
    # Parse diseases
    diseases = parse_orphanet_diseases(diseases_xml)
    
    # Parse clinical signs
    symptoms = {}
    clinical_xml = RAW_DIR / "orphanet_clinical_signs.xml"
    if clinical_xml.exists():
        symptoms = parse_orphanet_clinical_signs(clinical_xml)
    else:
        logger.warning(f"Not found: {clinical_xml}")

    # Parse genes
    genes = {}
    genes_xml = RAW_DIR / "orphanet_genes.xml"
    if genes_xml.exists():
        genes = parse_orphanet_genes(genes_xml)
    else:
        logger.warning(f"Not found: {genes_xml}")

    # Parse prevalence
    prevalence = {}
    prevalence_xml = RAW_DIR / "orphanet_prevalence.xml"
    if prevalence_xml.exists():
        prevalence = parse_orphanet_prevalence(prevalence_xml)
    else:
        logger.warning(f"Not found: {prevalence_xml}")

    # Merge data
    merged_diseases = merge_disease_data(diseases, symptoms, genes, prevalence)
    
    # Save to JSON
    output_path = PROCESSED_DIR / "rare_diseases_knowledge_base.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_diseases, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✓ Saved knowledge base to {output_path}")
    logger.info(f"Total diseases: {len(merged_diseases)}")
    
    # Summary
    with_symptoms = sum(1 for d in merged_diseases if d.get("symptoms"))
    with_genes    = sum(1 for d in merged_diseases if d.get("genes"))
    with_prev     = sum(1 for d in merged_diseases if d.get("prevalence"))
    logger.info(f"  With symptoms:   {with_symptoms}")
    logger.info(f"  With genes:      {with_genes}")
    logger.info(f"  With prevalence: {with_prev}")


if __name__ == "__main__":
    main()
