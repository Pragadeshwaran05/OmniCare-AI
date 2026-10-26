# ============================================================
# OMNICARE AI — MEDICAL RECORD NORMALIZER
# ============================================================

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union


# ------------------------------------------------------------
# DATE NORMALIZATION
# ------------------------------------------------------------

DATE_PATTERNS = [
    # ISO formats
    r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$",
    # YYYY-MM-DD
    r"^(\d{4})-(\d{2})-(\d{2})$",
    # DD-MM-YYYY
    r"^(\d{2})-(\d{2})-(\d{4})$",
    # DD/MM/YYYY
    r"^(\d{2})/(\d{2})/(\d{4})$",
    # DD Mon YYYY (e.g., 09 Oct 2026, 9 October 2026)
    r"^(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})$",
    # Mon DD, YYYY (e.g., Oct 09, 2026)
    r"^([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})$",
]

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_strict_date(date_str: Any) -> Optional[datetime]:
    """
    Strictly parse a date string into a datetime object (naive, midnight UTC).
    Rejects invalid dates (e.g., Feb 30, invalid month numbers).
    Converts unambiguous formats like DD-MM-YYYY and DD Mon YYYY.
    Returns None if date_str cannot be parsed into a real calendar date.
    """
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str.replace(tzinfo=None)

    s = str(date_str).strip()
    if not s:
        return None

    # Check for ISO format with time
    iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})[T ]", s)
    if iso_match:
        try:
            # Handle ISO string with potential Z or offsets
            clean_s = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_s)
            return dt.replace(tzinfo=None)
        except Exception:
            pass

    # YYYY-MM-DD
    m_ymd = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m_ymd:
        y, m, d = int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3))
        try:
            return datetime(y, m, d)
        except ValueError:
            return None

    # DD-MM-YYYY or DD/MM/YYYY
    m_dmy = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if m_dmy:
        d, m, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        try:
            return datetime(y, m, d)
        except ValueError:
            return None

    # DD Mon YYYY (e.g., 09 Oct 2026, 9 October 2026)
    m_named = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})$", s)
    if m_named:
        d = int(m_named.group(1))
        mon_str = m_named.group(2).lower()
        y = int(m_named.group(3))
        m = MONTH_MAP.get(mon_str)
        if m:
            try:
                return datetime(y, m, d)
            except ValueError:
                return None

    # Mon DD, YYYY (e.g., October 09, 2026)
    m_named2 = re.match(r"^([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})$", s)
    if m_named2:
        mon_str = m_named2.group(1).lower()
        d = int(m_named2.group(2))
        y = int(m_named2.group(3))
        m = MONTH_MAP.get(mon_str)
        if m:
            try:
                return datetime(y, m, d)
            except ValueError:
                return None

    return None


def format_iso_date(dt_or_str: Any) -> Optional[str]:
    """
    Convert any valid date string or datetime into standardized YYYY-MM-DD.
    Returns None if invalid.
    """
    dt = parse_strict_date(dt_or_str)
    return dt.strftime("%Y-%m-%d") if dt else None


# ------------------------------------------------------------
# FOLLOW-UP DATE EXTRACTION
# ------------------------------------------------------------

def extract_followup_date(followup_text: Any) -> Optional[datetime]:
    """
    Extract a concrete follow-up date from unstructured doctor follow-up notes.
    Examples:
      - "09 Oct 2026 (After 7 days) or SOS if breathlessness occurs." -> 2026-10-09
      - "12 October 2026" -> 2026-10-12
      - "Follow up on 2026-10-30" -> 2026-10-30
      - "Review in 2 weeks" -> returns None (relative without anchor)
    """
    if not followup_text:
        return None

    text = str(followup_text).strip()

    # Try explicit DD Mon YYYY inside text (e.g., '09 Oct 2026')
    m_named = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b", text)
    if m_named:
        d = int(m_named.group(1))
        mon_str = m_named.group(2).lower()
        y = int(m_named.group(3))
        m = MONTH_MAP.get(mon_str)
        if m:
            try:
                return datetime(y, m, d)
            except ValueError:
                pass

    # Try YYYY-MM-DD inside text
    m_ymd = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if m_ymd:
        y, m, d = int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3))
        try:
            return datetime(y, m, d)
        except ValueError:
            pass

    # Try DD-MM-YYYY or DD/MM/YYYY
    m_dmy = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", text)
    if m_dmy:
        d, m, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        try:
            return datetime(y, m, d)
        except ValueError:
            pass

    return None


# ------------------------------------------------------------
# MEASUREMENT & NUMERIC NORMALIZATION
# ------------------------------------------------------------

def normalize_numeric_value(val: Any) -> Optional[float]:
    """
    Safely parse numeric test result from various string formats:
    "142" -> 142.0
    "142.5 mg/dL" -> 142.5
    " < 140 " -> 140.0
    "Within normal limits" -> None
    """
    if val is None:
        return None

    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if not s:
        return None

    # Remove inequality signs and extra symbols
    cleaned = re.sub(r"^[<>=~±\s]+", "", s)
    # Extract first float or integer
    m = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if m:
        try:
            return float(m.group(0))
        except ValueError:
            return None

    return None


def parse_blood_pressure(val: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract systolic and diastolic from strings like '130/85', '140 / 90 mmHg'.
    Returns (systolic, diastolic) or (None, None).
    """
    if not val:
        return None, None

    s = str(val).strip()
    m = re.search(r"(\d{2,3})\s*[/–-]\s*(\d{2,3})", s)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            return None, None
    return None, None


def normalize_unit(unit_str: Any) -> str:
    """
    Standardize clinical measurement units.
    """
    if not unit_str:
        return ""

    u = str(unit_str).strip().lower()
    mapping = {
        "mg/dl": "mg/dL",
        "mg/100ml": "mg/dL",
        "%": "%",
        "percent": "%",
        "g/dl": "g/dL",
        "gm/dl": "g/dL",
        "mmhg": "mmHg",
        "bpm": "bpm",
        "/min": "bpm",
        "u/l": "U/L",
        "iu/l": "IU/L",
        "fl": "fL",
        "pg": "pg",
        "cells/cumm": "cells/cu.mm",
        "/cumm": "/cu.mm",
    }
    return mapping.get(u, str(unit_str).strip())


# ------------------------------------------------------------
# TIMELINE RECORD NORMALIZATION
# ------------------------------------------------------------

def normalize_timeline_event(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a raw health_timeline_events row into a normalized dictionary
    with parsed dates, validated lists, and clean structure.
    """
    raw_date = raw_event.get("event_date")
    parsed_date = parse_strict_date(raw_date)
    iso_date = parsed_date.strftime("%Y-%m-%d") if parsed_date else None

    # Investigations normalization
    raw_invs = raw_event.get("investigations") or []
    if not isinstance(raw_invs, list):
        raw_invs = []

    normalized_invs = []
    for inv in raw_invs:
        if not isinstance(inv, dict):
            continue
        name = str(inv.get("name") or "").strip()
        if not name:
            continue
        raw_result = inv.get("result")
        num_result = normalize_numeric_value(raw_result)
        raw_unit = inv.get("unit")
        unit = normalize_unit(raw_unit)

        normalized_invs.append({
            "name": name,
            "raw_result": raw_result,
            "numeric_result": num_result,
            "unit": unit,
            "reference_range": inv.get("reference_range"),
            "event_date": iso_date,
            "medical_record_id": raw_event.get("medical_record_id"),
        })

    # Medications normalization
    raw_meds = raw_event.get("medications") or []
    if not isinstance(raw_meds, list):
        raw_meds = []

    normalized_meds = []
    for med in raw_meds:
        if not isinstance(med, dict):
            continue
        med_name = str(med.get("name") or "").strip()
        if not med_name:
            continue

        normalized_meds.append({
            "name": med_name,
            "dose": med.get("dose"),
            "frequency": med.get("frequency"),
            "duration": med.get("duration"),
            "instructions": med.get("instructions"),
            "route": med.get("route"),
            "event_date": iso_date,
            "medical_record_id": raw_event.get("medical_record_id"),
        })

    # Follow-up parsing
    raw_followup = raw_event.get("follow_up")
    followup_dt = extract_followup_date(raw_followup)
    followup_iso = followup_dt.strftime("%Y-%m-%d") if followup_dt else None

    return {
        "id": raw_event.get("id"),
        "patient_id": raw_event.get("patient_id"),
        "medical_record_id": raw_event.get("medical_record_id"),
        "event_date": iso_date,
        "event_datetime": parsed_date,
        "event_type": raw_event.get("event_type") or "other",
        "provider_name": raw_event.get("provider_name"),
        "hospital_name": raw_event.get("hospital_name"),
        "diagnosis": raw_event.get("diagnosis"),
        "clinical_findings": raw_event.get("clinical_findings"),
        "investigations": normalized_invs,
        "medications": normalized_meds,
        "raw_follow_up": raw_followup,
        "follow_up_date": followup_iso,
        "follow_up_datetime": followup_dt,
        "clinical_summary": raw_event.get("clinical_summary"),
        "created_at": raw_event.get("created_at"),
    }
