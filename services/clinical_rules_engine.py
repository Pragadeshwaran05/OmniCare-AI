# ============================================================
# OMNICARE AI — CLINICAL RULES ENGINE
# ============================================================

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.medical_record_normalizer import (
    parse_strict_date,
    normalize_numeric_value,
    parse_blood_pressure,
)


# ------------------------------------------------------------
# CLINICAL REFERENCE RANGES & CLASSIFIERS
# ------------------------------------------------------------

def evaluate_investigation(
    name: str,
    value: Any,
    unit: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate an individual investigation result deterministically against
    established clinical guidelines.
    Returns:
      {
        "test_name": str,
        "value": Any,
        "numeric_value": Optional[float],
        "unit": str,
        "is_abnormal": bool,
        "severity": "normal" | "low" | "medium" | "high",
        "status": "normal" | "borderline" | "elevated" | "high" | "critical" | "low",
        "rule_id": str,
        "explanation": str,
        "reference_range": str
      }
    """
    clean_name = str(name or "").strip()
    norm_name = clean_name.lower()
    num_val = normalize_numeric_value(value)
    clean_unit = str(unit or "").strip()

    result = {
        "test_name": clean_name,
        "value": value,
        "numeric_value": num_val,
        "unit": clean_unit,
        "is_abnormal": False,
        "severity": "normal",
        "status": "normal",
        "rule_id": "RULE_DEFAULT_NORMAL",
        "explanation": "Result is within expected parameters or has no numeric rule.",
        "reference_range": "Clinician correlation required"
    }

    # If BP is in text format like "145/95"
    if any(k in norm_name for k in ["blood pressure", "bp", "hypertension"]):
        sys_val, dia_val = parse_blood_pressure(value)
        if sys_val is not None and dia_val is not None:
            result["reference_range"] = "< 120 / < 80 mmHg"
            result["unit"] = clean_unit or "mmHg"
            if sys_val >= 180 or dia_val >= 120:
                result.update({
                    "is_abnormal": True,
                    "severity": "high",
                    "status": "critical",
                    "rule_id": "RULE_BP_HYPERTENSIVE_CRISIS",
                    "explanation": f"Blood pressure {sys_val:.0f}/{dia_val:.0f} mmHg indicates hypertensive crisis (>= 180/120 mmHg)."
                })
            elif sys_val >= 140 or dia_val >= 90:
                result.update({
                    "is_abnormal": True,
                    "severity": "high",
                    "status": "high",
                    "rule_id": "RULE_BP_STAGE2_HYPERTENSION",
                    "explanation": f"Blood pressure {sys_val:.0f}/{dia_val:.0f} mmHg indicates Stage 2 hypertension (>= 140/90 mmHg)."
                })
            elif sys_val >= 130 or dia_val >= 80:
                result.update({
                    "is_abnormal": True,
                    "severity": "medium",
                    "status": "elevated",
                    "rule_id": "RULE_BP_STAGE1_HYPERTENSION",
                    "explanation": f"Blood pressure {sys_val:.0f}/{dia_val:.0f} mmHg indicates Stage 1 hypertension (130-139 / 80-89 mmHg)."
                })
            return result

    if num_val is None:
        # Check text result for common abnormal phrases
        text_val = str(value or "").lower()
        if any(w in text_val for w in ["abnormal", "positive", "reactive", "detected", "high", "elevated", "critical"]):
            result.update({
                "is_abnormal": True,
                "severity": "medium",
                "status": "abnormal",
                "rule_id": "RULE_TEXT_FLAGGED_ABNORMAL",
                "explanation": f"Documented qualitative result '{value}' indicates an abnormal finding."
            })
        return result

    # Fasting Blood Glucose / Sugar
    if re.search(r"\b(fasting\s+(?:blood\s+)?(?:glucose|sugar)|fbs)\b", norm_name):
        result["reference_range"] = "70 – 99 mg/dL"
        if num_val >= 250 or num_val <= 50:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "critical",
                "rule_id": "RULE_FBS_CRITICAL",
                "explanation": f"Fasting glucose {num_val} mg/dL is at critical level (<=50 or >=250 mg/dL)."
            })
        elif num_val >= 126:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "high",
                "rule_id": "RULE_FBS_DIABETIC",
                "explanation": f"Fasting glucose {num_val} mg/dL exceeds normal limit (99 mg/dL) and meets diabetes threshold (>= 126 mg/dL)."
            })
        elif num_val >= 100:
            result.update({
                "is_abnormal": True, "severity": "medium", "status": "borderline",
                "rule_id": "RULE_FBS_IMPAIRED",
                "explanation": f"Fasting glucose {num_val} mg/dL is in impaired fasting glucose range (100–125 mg/dL)."
            })
        elif num_val < 70:
            result.update({
                "is_abnormal": True, "severity": "medium", "status": "low",
                "rule_id": "RULE_FBS_HYPOGLYCEMIA",
                "explanation": f"Fasting glucose {num_val} mg/dL indicates hypoglycemia (< 70 mg/dL)."
            })
        return result

    # Post Prandial / Random Blood Glucose
    if re.search(r"\b(post\s*prandial|ppbs|pp\s+glucose|random\s+(?:blood\s+)?(?:glucose|sugar)|rbs)\b", norm_name):
        result["reference_range"] = "< 140 mg/dL"
        if num_val >= 300 or num_val <= 50:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "critical",
                "rule_id": "RULE_PPBS_CRITICAL",
                "explanation": f"Blood glucose {num_val} mg/dL is at critical level."
            })
        elif num_val >= 200:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "high",
                "rule_id": "RULE_PPBS_DIABETIC",
                "explanation": f"Post-prandial / random glucose {num_val} mg/dL meets diabetes threshold (>= 200 mg/dL)."
            })
        elif num_val >= 140:
            result.update({
                "is_abnormal": True, "severity": "medium", "status": "borderline",
                "rule_id": "RULE_PPBS_IMPAIRED",
                "explanation": f"Post-prandial glucose {num_val} mg/dL indicates impaired glucose tolerance (140–199 mg/dL)."
            })
        return result

    # General Glucose
    if re.search(r"\b(glucose|sugar)\b", norm_name):
        result["reference_range"] = "70 – 140 mg/dL"
        if num_val >= 200:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "high",
                "rule_id": "RULE_GLUCOSE_HIGH",
                "explanation": f"Blood glucose {num_val} mg/dL is elevated above normal."
            })
        elif num_val >= 140:
            result.update({
                "is_abnormal": True, "severity": "medium", "status": "borderline",
                "rule_id": "RULE_GLUCOSE_ELEVATED",
                "explanation": f"Blood glucose {num_val} mg/dL exceeds normal limit (140 mg/dL)."
            })
        return result

    # HbA1c
    if re.search(r"\b(hba1c|glycated\s+hemoglobin|a1c)\b", norm_name):
        result["reference_range"] = "4.0 – 5.6 %"
        if num_val >= 9.0:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "critical",
                "rule_id": "RULE_HBA1C_VERY_HIGH",
                "explanation": f"HbA1c {num_val}% indicates severely uncontrolled diabetes (>= 9.0%)."
            })
        elif num_val >= 8.0:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "high",
                "rule_id": "RULE_HBA1C_POOR_CONTROL",
                "explanation": f"HbA1c {num_val}% indicates poorly controlled diabetes (>= 8.0%)."
            })
        elif num_val >= 6.5:
            result.update({
                "is_abnormal": True, "severity": "medium", "status": "elevated",
                "rule_id": "RULE_HBA1C_DIABETIC",
                "explanation": f"HbA1c {num_val}% meets diagnostic threshold for diabetes (>= 6.5%)."
            })
        elif num_val >= 5.7:
            result.update({
                "is_abnormal": True, "severity": "low", "status": "borderline",
                "rule_id": "RULE_HBA1C_PREDIABETES",
                "explanation": f"HbA1c {num_val}% indicates pre-diabetes range (5.7–6.4%)."
            })
        return result

    # Total Cholesterol
    if re.search(r"\b(total\s+cholesterol|serum\s+cholesterol)\b", norm_name):
        result["reference_range"] = "< 200 mg/dL"
        if num_val >= 240:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "high",
                "rule_id": "RULE_CHOL_HIGH",
                "explanation": f"Total cholesterol {num_val} mg/dL indicates hypercholesterolemia (>= 240 mg/dL)."
            })
        elif num_val >= 200:
            result.update({
                "is_abnormal": True, "severity": "medium", "status": "borderline",
                "rule_id": "RULE_CHOL_BORDERLINE",
                "explanation": f"Total cholesterol {num_val} mg/dL is borderline elevated (200–239 mg/dL)."
            })
        return result

    # LDL Cholesterol
    if re.search(r"\b(ldl(?:\s+cholesterol)?)\b", norm_name):
        result["reference_range"] = "< 100 mg/dL"
        if num_val >= 160:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "high",
                "rule_id": "RULE_LDL_HIGH",
                "explanation": f"LDL cholesterol {num_val} mg/dL is elevated in high-risk range (>= 160 mg/dL)."
            })
        elif num_val >= 130:
            result.update({
                "is_abnormal": True, "severity": "medium", "status": "borderline",
                "rule_id": "RULE_LDL_BORDERLINE",
                "explanation": f"LDL cholesterol {num_val} mg/dL is borderline high (130–159 mg/dL)."
            })
        return result

    # Triglycerides
    if re.search(r"\b(triglycerides?|tg)\b", norm_name):
        result["reference_range"] = "< 150 mg/dL"
        if num_val >= 500:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "critical",
                "rule_id": "RULE_TG_VERY_HIGH",
                "explanation": f"Triglycerides {num_val} mg/dL are severely elevated (>= 500 mg/dL, pancreatitis risk)."
            })
        elif num_val >= 200:
            result.update({
                "is_abnormal": True, "severity": "medium", "status": "high",
                "rule_id": "RULE_TG_HIGH",
                "explanation": f"Triglycerides {num_val} mg/dL are elevated (>= 200 mg/dL)."
            })
        elif num_val >= 150:
            result.update({
                "is_abnormal": True, "severity": "low", "status": "borderline",
                "rule_id": "RULE_TG_BORDERLINE",
                "explanation": f"Triglycerides {num_val} mg/dL are borderline elevated (150–199 mg/dL)."
            })
        return result

    # Serum Creatinine
    if re.search(r"\b(creatinine|serum\s+creatinine)\b", norm_name):
        result["reference_range"] = "0.6 – 1.2 mg/dL"
        if num_val >= 3.0:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "critical",
                "rule_id": "RULE_CREATININE_CRITICAL",
                "explanation": f"Serum creatinine {num_val} mg/dL indicates severe renal impairment."
            })
        elif num_val >= 1.4:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "high",
                "rule_id": "RULE_CREATININE_ELEVATED",
                "explanation": f"Serum creatinine {num_val} mg/dL exceeds normal adult range (0.6–1.2 mg/dL)."
            })
        return result

    # Hemoglobin
    if re.search(r"\b(hemoglobin|hb)\b", norm_name):
        result["reference_range"] = "12.0 – 17.5 g/dL"
        if num_val < 7.0:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "critical",
                "rule_id": "RULE_HB_CRITICAL_ANEMIA",
                "explanation": f"Hemoglobin {num_val} g/dL indicates severe life-threatening anemia (< 7.0 g/dL)."
            })
        elif num_val < 10.0:
            result.update({
                "is_abnormal": True, "severity": "high", "status": "high",
                "rule_id": "RULE_HB_MODERATE_ANEMIA",
                "explanation": f"Hemoglobin {num_val} g/dL indicates moderate anemia (< 10.0 g/dL)."
            })
        elif num_val < 12.0:
            result.update({
                "is_abnormal": True, "severity": "medium", "status": "low",
                "rule_id": "RULE_HB_MILD_ANEMIA",
                "explanation": f"Hemoglobin {num_val} g/dL is below normal reference threshold (12.0 g/dL)."
            })
        return result

    return result


# ------------------------------------------------------------
# OVERDUE FOLLOW-UP CHECKER
# ------------------------------------------------------------

def check_followup_overdue(
    followup_date_str_or_dt: Any,
    reference_dt: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """
    Check if a documented follow-up is overdue against a reference date (default: now UTC).
    Returns None if not overdue or invalid.
    Returns:
      {
        "due_date": "YYYY-MM-DD",
        "days_overdue": int,
        "is_overdue": bool,
        "severity": "medium" | "high"
      }
    """
    if not followup_date_str_or_dt:
        return None

    dt = parse_strict_date(followup_date_str_or_dt)
    if not dt:
        return None

    ref = reference_dt or datetime.now(timezone.utc)
    if hasattr(ref, "date"):
        ref_date = ref.date()
    else:
        ref_date = ref

    due_date = dt.date()
    if due_date < ref_date:
        days = (ref_date - due_date).days
        return {
            "due_date": due_date.strftime("%Y-%m-%d"),
            "days_overdue": days,
            "is_overdue": True,
            "severity": "high" if days > 14 else "medium"
        }

    return None
