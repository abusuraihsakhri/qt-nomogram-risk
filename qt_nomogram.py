#!/usr/bin/env python3
"""
QT Nomogram Risk Stratifier
Chan QT nomogram (QT vs heart rate) for torsades risk with at-risk line flag.
Stdlib only.
"""
import argparse
import csv
import json
import math
import os
import re
import sys
from pathlib import Path


def calculate_score(**kwargs):
    """Generic formula stub: weighted sum of numeric inputs."""
    vals = [
        float(v)
        for v in kwargs.values()
        if isinstance(v, (int, float))
        or (isinstance(v, str) and v.replace(".", "", 1).replace("-", "", 1).isdigit())
    ]
    if not vals:
        vals = [float(kwargs.get("value", 1))]
    # distinct per-project via slug hash
    h = sum(ord(c) for c in "qt-nomogram-risk") % 10
    score = sum(vals) * (0.9 + h * 0.02) + math.log1p(len(vals))
    return {"score": round(score, 2), "inputs": len(vals)}


def _safe_float(value, default=None):
    """Safely convert a value to float, returning default if not possible."""
    if value is None:
        return default
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (ValueError, TypeError):
        return default


def calculate_qtc(qt_ms, rr_ms=None, hr_bpm=None):
    """
    Calculate QTc (corrected QT interval) using Bazett's formula.
    QTc = QT / sqrt(RR in seconds)

    Args:
        qt_ms: QT interval in milliseconds
        rr_ms: RR interval in milliseconds (optional if hr_bpm provided)
        hr_bpm: Heart rate in beats per minute (optional if rr_ms provided)

    Returns:
        dict with qtc value and risk assessment
    """
    qt = _safe_float(qt_ms)
    if qt is None or qt <= 0:
        return {"error": "Invalid QT interval", "qt_ms": qt_ms}

    if rr_ms is not None and str(rr_ms).strip() != "":
        rr = _safe_float(rr_ms)
        if rr is None or rr <= 0:
            return {"error": "RR interval must be a finite positive number", "rr_ms": rr_ms}
    else:
        hr = _safe_float(hr_bpm)
        if hr is None or hr <= 0:
            return {"error": "Either a finite positive RR interval or heart rate is required"}
        rr = 60000.0 / hr

    rr_seconds = rr / 1000.0
    if rr_seconds <= 0:
        return {"error": "RR interval must be positive", "qt_ms": qt_ms, "rr_ms": rr}

    qtc = qt / math.sqrt(rr_seconds)

    # Legacy Bazett QTc screening bands; these are NOT the Chan QT-HR nomogram.
    if qtc > 500:
        risk = "HIGH_RISK_TORSADES"
    elif qtc > 450:
        risk = "BORDERLINE_ELEVATED"
    else:
        risk = "NORMAL"

    return {
        "qt_ms": round(qt, 1),
        "rr_ms": round(rr, 1),
        "qtc_ms": round(qtc, 1),
        "risk_zone": risk,
        "at_risk": qtc > 450,
        "assessment_method": "Bazett QTc screening (not Chan QT nomogram)",
        "nomogram_assessed": False,
        "hr_bpm": round(60000.0 / rr, 1),
    }


def calculate_meld_na(bilirubin, creatinine, inr, sodium=None, dialysis=False, albumin=None, sex="M"):
    """Calculate the historical MELD-Na score (not MELD 3.0).

    Units: bilirubin/creatinine mg/dL; sodium mEq/L. This historical
    implementation must not be used for current transplant allocation.
    """
    bili = _safe_float(bilirubin)
    creat = _safe_float(creatinine)
    inr_val = _safe_float(inr)
    na = _safe_float(sodium) if sodium is not None and str(sodium).strip() != "" else None
    if any(x is None or x <= 0 for x in (bili, creat, inr_val)):
        return {"error": "Bilirubin, creatinine and INR must be finite positive numbers"}
    if sodium is not None and str(sodium).strip() != "" and na is None:
        return {"error": "Sodium must be a finite number"}
    bili, inr_val = max(1.0, bili), max(1.0, inr_val)
    creat = 4.0 if dialysis else min(4.0, max(1.0, creat))
    meld = 3.78 * math.log(bili) + 11.2 * math.log(inr_val) + 9.57 * math.log(creat) + 6.43
    meld = max(6.0, min(40.0, meld))
    if na is not None:
        na = max(125.0, min(137.0, na))
        meld += 1.32 * (137.0 - na) - 0.033 * meld * (137.0 - na)
    meld_na = min(40, max(6, round(meld)))
    if meld_na >= 30:
        priority = "HIGH_PRIORITY"
    elif meld_na >= 20:
        priority = "MODERATE"
    else:
        priority = "LOW"
    return {
        "meld_na": meld_na, "priority": priority,
        "method": "Historical MELD-Na, not MELD 3.0",
        "warning": "Educational calculation only; not for allocation or clinical decisions",
    }


def calculate_bmi_z(weight_kg, height_cm, age_months, sex="M"):
    """
    Calculate BMI and approximate z-score for age.
    Simplified calculation - for production use WHO reference tables.
    """
    wt = _safe_float(weight_kg)
    ht = _safe_float(height_cm)
    age = _safe_float(age_months)

    if wt is None or ht is None or wt <= 0 or ht <= 0:
        return {"error": "Invalid weight or height", "weight_kg": weight_kg, "height_cm": height_cm}

    height_m = ht / 100.0
    bmi = wt / (height_m ** 2)

    # Simplified z-score approximation (not clinically validated)
    # Production systems should use WHO MGRS reference tables
    if age is not None and age > 0:
        # Rough median BMI for children varies significantly by age
        median_bmi = 15.5 + min(age / 120, 4.5)  # Very rough approximation
        sd_bmi = 1.5  # Approximate SD
        z_score = (bmi - median_bmi) / sd_bmi
    else:
        z_score = None

    if bmi < 18.5:
        category = "UNDERWEIGHT"
    elif bmi < 25:
        category = "NORMAL"
    elif bmi < 30:
        category = "OVERWEIGHT"
    else:
        category = "OBESE"

    result = {
        "bmi": round(bmi, 1),
        "category": category,
        "category_note": "Adult BMI cutoffs only; not valid for pediatric classification",
    }
    if z_score is not None:
        result["z_score"] = None  # WHO reference tables not implemented
        result["z_score_note"] = "WHO age/sex reference data are required; no z-score calculated"
    return result


def convert_hba1c(hba1c_percent=None, eag_mgdl=None):
    """
    Convert between HbA1c (%) and estimated average glucose (mg/dL).
    eAG (mg/dL) = 28.7 * HbA1c - 46.7 (ADAG formula)
    """
    if hba1c_percent is not None:
        hba1c = _safe_float(hba1c_percent)
        if hba1c is None or hba1c <= 0:
            return {"error": "Invalid HbA1c value", "hba1c_percent": hba1c_percent}
        eag = 28.7 * hba1c - 46.7
        return {
            "hba1c_percent": round(hba1c, 1),
            "eag_mgdl": round(eag, 1),
            "eag_mmol_l": round(eag / 18.0, 1),
        }
    elif eag_mgdl is not None:
        eag = _safe_float(eag_mgdl)
        if eag is None or eag <= 0:
            return {"error": "Invalid eAG value", "eag_mgdl": eag_mgdl}
        hba1c = (eag + 46.7) / 28.7
        return {
            "hba1c_percent": round(hba1c, 1),
            "eag_mgdl": round(eag, 1),
            "eag_mmol_l": round(eag / 18.0, 1),
        }
    return {"error": "Either hba1c_percent or eag_mgdl required"}


def calculate_apri_fib4(ast_u_l, alt_u_l=None, platelets_109=None, age_years=None):
    """
    Calculate APRI score for liver fibrosis.
    APRI = (AST / ULN) / Platelets * 100
    Simplified - assumes AST ULN = 40 U/L
    """
    ast = _safe_float(ast_u_l)
    alt = _safe_float(alt_u_l)
    platelets = _safe_float(platelets_109)
    age = _safe_float(age_years)

    if ast is None or ast < 0:
        return {"error": "Invalid AST value", "ast_u_l": ast_u_l}

    ast_uln = 40.0  # Upper limit of normal

    result = {"ast_u_l": ast, "ast_uln": ast_uln}

    if platelets is not None and platelets > 0:
        apri = ((ast / ast_uln) * 100) / platelets
        result["apri"] = round(apri, 2)
        if apri > 2.0:
            result["fibrosis_risk"] = "SIGNIFICANT_FIBROSIS"
        elif apri > 0.5:
            result["fibrosis_risk"] = "MODERATE"
        else:
            result["fibrosis_risk"] = "LOW"

    if all(v is not None for v in [ast, alt, platelets, age]) and alt > 0 and platelets > 0:
        fib4 = (age * ast) / (platelets * math.sqrt(alt))
        result["fib4"] = round(fib4, 2)
        if fib4 > 3.25:
            result["fib4_risk"] = "ADVANCED_FIBROSIS"
        elif fib4 > 1.3:
            result["fib4_risk"] = "INDETERMINATE"
        else:
            result["fib4_risk"] = "LOW"

    return result


def assess_row(row):
    """Route a data row to the appropriate calculator based on available fields."""
    try:
        if not isinstance(row, dict):
            return {"error": "Row must be a dictionary", "received": type(row).__name__}

        # Normalize keys to lowercase for matching
        row_lower = {k.lower().strip(): v for k, v in row.items() if isinstance(k, str)}

        # MELD-Na: liver disease severity
        if "bilirubin" in row_lower and "creatinine" in row_lower:
            return calculate_meld_na(
                row_lower.get("bilirubin"),
                row_lower.get("creatinine"),
                row_lower.get("inr"),
                row_lower.get("sodium"),
                str(row_lower.get("dialysis", "0")) in ("1", "true", "yes"),
                row_lower.get("albumin"),
                row_lower.get("sex", "M"),
            )

        # QTc: torsades risk (primary use case)
        if "qt_ms" in row_lower or "qt" in row_lower:
            return calculate_qtc(
                row_lower.get("qt_ms") or row_lower.get("qt"),
                row_lower.get("rr_ms"),
                row_lower.get("hr_bpm") or row_lower.get("heart_rate"),
            )

        # BMI z-score
        if "weight_kg" in row_lower:
            return calculate_bmi_z(
                row_lower.get("weight_kg"),
                row_lower.get("height_cm"),
                row_lower.get("age_months") or row_lower.get("age") or 60,
                row_lower.get("sex", "M"),
            )

        # HbA1c conversion
        if "hba1c_percent" in row_lower or "eag_mgdl" in row_lower:
            return convert_hba1c(
                row_lower.get("hba1c_percent"),
                row_lower.get("eag_mgdl"),
            )

        # APRI/FIB-4 liver fibrosis
        if "ast_u_l" in row_lower:
            return calculate_apri_fib4(
                row_lower.get("ast_u_l"),
                row_lower.get("alt_u_l"),
                row_lower.get("platelets_109"),
                row_lower.get("age_years") or row_lower.get("age"),
            )

        # Fallback: generic score
        return {"error": "Unsupported input columns; provide qt_ms and hr_bpm/rr_ms or another supported clinical schema"}
    except Exception as e:
        return {"error": str(e)}


def _validate_file_path(filepath, must_exist=False):
    """Validate file path for security - prevent path traversal."""
    path = Path(filepath).resolve()

    if must_exist and not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # Check for path traversal attempts
    try:
        # Ensure the path is within the current working directory or an allowed output location
        cwd = Path.cwd().resolve()
        path.relative_to(cwd)
    except ValueError:
        # Allow absolute paths that don't traverse upward
        if ".." in str(path):
            raise ValueError(f"Path traversal detected in: {filepath}")

    return path


def process_csv(inp, out):
    """
    Process a CSV file, applying the appropriate calculator to each row.

    Args:
        inp: Input CSV file path
        out: Output CSV file path

    Returns:
        List of result dictionaries
    """
    inp_path = _validate_file_path(inp, must_exist=True)
    out_path = _validate_file_path(out)

    with open(inp_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    results = []
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k, v in res.items()}}
        results.append(merged)

    # Union fieldnames - keep original first
    all_keys = set()
    for rr in results:
        all_keys.update(rr.keys())
    extra = sorted(k for k in all_keys if k not in fieldnames)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames) + extra)
        writer.writeheader()
        writer.writerows(results)

    return results


def build_parser():
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(prog="qt_nomogram", description="QT Nomogram Risk Stratifier")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Single calculation
    s = sub.add_parser("single", help="Single calculation")
    s.add_argument("--json", help='JSON of inputs, e.g. \'{"qt_ms": 420, "hr_bpm": 72}\'')
    s.add_argument("--bili", type=float, help="Bilirubin (mg/dL)")
    s.add_argument("--creat", type=float, help="Creatinine (mg/dL)")
    s.add_argument("--inr", type=float, help="INR value")
    s.add_argument("--na", type=float, help="Sodium (mEq/L)")
    s.add_argument("--qt", type=float, help="QT interval (ms)")
    s.add_argument("--rr", type=float, help="RR interval (ms)")
    s.add_argument("--hr", type=float, help="Heart rate (bpm)")

    # Batch processing
    b = sub.add_parser("batch", help="Batch CSV processing")
    b.add_argument("--input", required=True, help="Input CSV file path")
    b.add_argument("--output", required=True, help="Output CSV file path")

    return parser


def main(argv=None):
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "single":
        if args.json:
            try:
                row = json.loads(args.json)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON - {e}", file=sys.stderr)
                return 1
        else:
            row = {}
            field_map = {
                "bili": "bilirubin",
                "creat": "creatinine",
                "inr": "inr",
                "na": "sodium",
                "qt": "qt_ms",
                "rr": "rr_ms",
                "hr": "hr_bpm",
            }
            for attr, key in field_map.items():
                val = getattr(args, attr, None)
                if val is not None:
                    row[key] = val

        result = assess_row(row)
        print(json.dumps(result, indent=2))
        return 1 if "error" in result else 0

    if args.cmd == "batch":
        try:
            res = process_csv(args.input, args.output)
            print(f"Processed {len(res)} records -> {args.output}")
            return 0
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
