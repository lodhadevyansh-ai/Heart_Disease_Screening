"""
Clinical Document Text Extraction and Structured Field Parser.

Extracts text from clinical PDF reports and parses structured physiological,
laboratory, and diagnostic values with clinical provenance, units, reference
intervals, and abnormal flags.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import pypdf


# Clinical extraction patterns with canonical test name, regex, default unit, and flag detection
PARSER_PATTERNS = [
    {
        "test_name": "cholesterol",
        "aliases": ["total_cholesterol", "chol"],
        "regex": re.compile(
            r"(?:Total\s+cholesterol|Cholesterol[,\s]+total)\s+([0-9]+(?:\.[0-9]+)?)\s*(mg/dL|mmol/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "mg/dL",
        "ref_high": 200.0,
        "ref_low": 100.0,
    },
    {
        "test_name": "ldl_cholesterol",
        "aliases": ["ldl"],
        "regex": re.compile(
            r"(?:LDL\s+cholesterol|LDL-C)\s+([0-9]+(?:\.[0-9]+)?)\s*(mg/dL|mmol/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "mg/dL",
        "ref_high": 100.0,
    },
    {
        "test_name": "hdl_cholesterol",
        "aliases": ["hdl"],
        "regex": re.compile(
            r"(?:HDL\s+cholesterol|HDL-C)\s+([0-9]+(?:\.[0-9]+)?)\s*(mg/dL|mmol/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "mg/dL",
        "ref_low": 40.0,
    },
    {
        "test_name": "triglycerides",
        "aliases": ["tg"],
        "regex": re.compile(
            r"Triglycerides\s+([0-9]+(?:\.[0-9]+)?)\s*(mg/dL|mmol/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "mg/dL",
        "ref_high": 150.0,
    },
    {
        "test_name": "fasting_glucose",
        "aliases": ["fbs", "glucose"],
        "regex": re.compile(
            r"(?:Fasting\s+glucose|Glucose[,\s]+fasting|Blood\s+glucose)\s+([0-9]+(?:\.[0-9]+)?)\s*(mg/dL|mmol/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "mg/dL",
        "ref_high": 100.0,
        "ref_low": 70.0,
    },
    {
        "test_name": "hba1c",
        "aliases": ["glycated_hemoglobin"],
        "regex": re.compile(
            r"(?:HbA1c|Glycated\s+hemoglobin|Hemoglobin\s+A1c)\s+([0-9]+(?:\.[0-9]+)?)\s*(%)?",
            re.IGNORECASE,
        ),
        "default_unit": "%",
        "ref_high": 5.7,
    },
    {
        "test_name": "troponin_i",
        "aliases": ["hs_ctni", "cardiac_troponin"],
        "regex": re.compile(
            r"(?:High-sensitivity\s+cardiac\s+troponin\s+I|hs-cTnI|Troponin\s+I)\s*\n?\(?[^\)]*\)?\s*\n?([0-9]+(?:\.[0-9]+)?)\s*(ng/L|pg/mL|mcg/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "ng/L",
        "ref_high": 14.0,
    },
    {
        "test_name": "bnp",
        "aliases": ["nt_probnp", "brain_natriuretic_peptide"],
        "regex": re.compile(
            r"(?:NT-proBNP|pro-BNP|BNP|Brain\s+Natriuretic\s+Peptide)\s*\n?([0-9]+(?:\.[0-9]+)?)\s*(pg/mL|ng/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "pg/mL",
        "ref_high": 125.0,
    },
    {
        "test_name": "hemoglobin",
        "aliases": ["hb", "hgb"],
        "regex": re.compile(
            r"(?:Hemoglobin|Hgb|Hb)\s+([0-9]+(?:\.[0-9]+)?)\s*(g/dL|g/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "g/dL",
        "ref_low": 12.0,
        "ref_high": 17.5,
    },
    {
        "test_name": "platelets",
        "aliases": ["platelet_count", "plt"],
        "regex": re.compile(
            r"(?:Platelet\s+count|Platelets)\s+([0-9]+(?:\.[0-9]+)?)\s*(10[■\^9]/L|k/uL|/mcL|k/mcL)?",
            re.IGNORECASE,
        ),
        "default_unit": "10^9/L",
        "ref_low": 150.0,
        "ref_high": 450.0,
    },
    {
        "test_name": "serum_creatinine",
        "aliases": ["creatinine"],
        "regex": re.compile(
            r"(?:Serum\s+creatinine|Creatinine)\s+([0-9]+(?:\.[0-9]+)?)\s*(mg/dL|umol/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "mg/dL",
        "ref_low": 0.6,
        "ref_high": 1.3,
    },
    {
        "test_name": "serum_sodium",
        "aliases": ["sodium"],
        "regex": re.compile(
            r"(?:Serum\s+sodium|Sodium)\s+([0-9]+(?:\.[0-9]+)?)\s*(mmol/L|mEq/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "mmol/L",
        "ref_low": 135.0,
        "ref_high": 145.0,
    },
    {
        "test_name": "potassium",
        "aliases": ["serum_potassium"],
        "regex": re.compile(
            r"(?:Serum\s+potassium|Potassium)\s+([0-9]+(?:\.[0-9]+)?)\s*(mmol/L|mEq/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "mmol/L",
        "ref_low": 3.5,
        "ref_high": 5.1,
    },
    {
        "test_name": "ejection_fraction",
        "aliases": ["lvef", "ef"],
        "regex": re.compile(
            r"(?:Left\s+ventricular\s+ejection\s+fraction|LVEF|Ejection\s+fraction)\s*(?:\([^\)]*\))?\s*\n?([0-9]+(?:\.[0-9]+)?)\s*(%)?",
            re.IGNORECASE,
        ),
        "default_unit": "%",
        "ref_low": 50.0,
        "ref_high": 75.0,
    },
    {
        "test_name": "creatinine_phosphokinase",
        "aliases": ["cpk", "ck"],
        "regex": re.compile(
            r"(?:Creatinine\s+phosphokinase|CPK|CK|Creatine\s+kinase)\s+([0-9]+(?:\.[0-9]+)?)\s*(U/L|mcg/L)?",
            re.IGNORECASE,
        ),
        "default_unit": "U/L",
        "ref_low": 20.0,
        "ref_high": 200.0,
    },
]


class ClinicalDocumentParser:
    """Parser to extract raw text and structured clinical values from documents."""

    @staticmethod
    def extract_text_from_pdf(file_path: Path) -> str:
        """Extract all raw text from a PDF document using pypdf."""
        if not file_path.exists():
            return ""
        text_parts = []
        try:
            reader = pypdf.PdfReader(str(file_path))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        except Exception:
            # Fallback to PyMuPDF if available
            try:
                import pymupdf
                doc = pymupdf.open(str(file_path))
                for page in doc:
                    text_parts.append(page.get_text())
                doc.close()
            except Exception:
                pass

        return "\n".join(text_parts)

    @classmethod
    def parse_clinical_text(cls, text: str) -> List[Dict[str, Any]]:
        """
        Scan extracted clinical text against supported test patterns and extract
        structured measurements with provenance.
        """
        if not text or not text.strip():
            return []

        extracted_measurements: List[Dict[str, Any]] = []
        seen_tests = set()

        # 1. Standard structured pattern matching
        for item in PARSER_PATTERNS:
            test_name = item["test_name"]
            pattern = item["regex"]
            match = pattern.search(text)
            if match:
                val_str = match.group(1)
                unit_str = match.group(2) if len(match.groups()) >= 2 and match.group(2) else item.get("default_unit", "")
                # Clean unit string
                if "■" in unit_str:
                    unit_str = unit_str.replace("■", "^9")

                try:
                    val_num = float(val_str)
                except ValueError:
                    val_num = None

                # Flag determination
                flag = "normal"
                ref_high = item.get("ref_high")
                ref_low = item.get("ref_low")
                if val_num is not None:
                    if ref_high is not None and val_num > ref_high:
                        flag = "high"
                    elif ref_low is not None and val_num < ref_low:
                        flag = "low"

                # Snippet context
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                snippet = text[start:end].replace("\n", " ").strip()

                extracted_measurements.append({
                    "test_name": test_name,
                    "value_numeric": val_num,
                    "value_text": str(val_str),
                    "unit": unit_str,
                    "reference_low": ref_low,
                    "reference_high": ref_high,
                    "flag": flag,
                    "source_context": snippet,
                })
                seen_tests.add(test_name)

        # 2. ECG findings parsing (ST-T abnormality, rhythm, rate)
        lower_text = text.lower()
        if "restecg" not in seen_tests:
            canonical_ecg = "normal"
            if "st-t" in lower_text or "st depression" in lower_text or "t-wave" in lower_text or "t wave" in lower_text:
                canonical_ecg = "st-t abnormality"
            elif "hypertrophy" in lower_text or "lvh" in lower_text:
                canonical_ecg = "lv hypertrophy"

            # Context snippet
            ecg_idx = lower_text.find("ecg")
            if ecg_idx != -1:
                snippet = text[max(0, ecg_idx - 20):min(len(text), ecg_idx + 120)].replace("\n", " ").strip()
            else:
                snippet = "ECG evaluation noted in report"

            extracted_measurements.append({
                "test_name": "restecg",
                "value_numeric": None,
                "value_text": canonical_ecg,
                "unit": None,
                "reference_low": None,
                "reference_high": None,
                "flag": "abnormal" if canonical_ecg != "normal" else "normal",
                "source_context": snippet,
            })
            seen_tests.add("restecg")

        # Heart rate extraction from ECG or vitals
        if "resting_heart_rate" not in seen_tests and "thalch" not in seen_tests:
            hr_match = re.search(r"(?:ventricular\s+rate|heart\s+rate|pulse|rate)[^\d\n]{0,30}(\d{2,3})\s*bpm", text, re.IGNORECASE)
            if hr_match:
                try:
                    hr_val = float(hr_match.group(1))
                    extracted_measurements.append({
                        "test_name": "resting_heart_rate",
                        "value_numeric": hr_val,
                        "value_text": str(int(hr_val)),
                        "unit": "bpm",
                        "reference_low": 60.0,
                        "reference_high": 100.0,
                        "flag": "high" if hr_val > 100 else ("low" if hr_val < 60 else "normal"),
                        "source_context": hr_match.group(0),
                    })
                    seen_tests.add("resting_heart_rate")
                except ValueError:
                    pass

        return extracted_measurements
