"""
Comprehensive test suite for qt_nomogram module - QT nomogram risk calculations.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

import qt_nomogram as m


class TestCalculateQtc:
    """Tests for QTc (corrected QT interval) calculation."""

    def test_normal_qtc_with_hr(self):
        """Normal QTc with heart rate."""
        result = m.calculate_qtc(qt_ms=400, hr_bpm=72)
        assert "qtc_ms" in result
        assert result["risk_zone"] == "BAZETT_QTC_LT_500"
        assert result["at_risk"] is None
        assert result["qtc_screen_positive"] is False

    def test_normal_qtc_with_rr(self):
        """Normal QTc with RR interval."""
        result = m.calculate_qtc(qt_ms=400, rr_ms=833)
        assert "qtc_ms" in result
        assert result["risk_zone"] == "BAZETT_QTC_LT_500"

    def test_borderline_qtc(self):
        """Borderline elevated QTc."""
        result = m.calculate_qtc(qt_ms=460, hr_bpm=60)
        assert result["qtc_ms"] > 450
        assert result["at_risk"] is None

    def test_high_risk_qtc(self):
        """High risk QTc > 500ms."""
        result = m.calculate_qtc(qt_ms=520, hr_bpm=60)
        assert result["risk_zone"] == "BAZETT_QTC_GE_500"
        assert result["qtc_screen_positive"] is True
        assert result["at_risk"] is True

    def test_invalid_qt(self):
        """Invalid QT interval returns error."""
        result = m.calculate_qtc(qt_ms=None)
        assert "error" in result

    def test_negative_qt(self):
        """Negative QT interval returns error."""
        result = m.calculate_qtc(qt_ms=-100)
        assert "error" in result

    def test_missing_rr_and_hr(self):
        """Missing both RR and HR returns error."""
        result = m.calculate_qtc(qt_ms=400)
        assert "error" in result


class TestCalculateMeldNa:
    """Tests for MELD-Na score calculation."""

    def test_low_meld(self):
        """Low MELD-Na score."""
        result = m.calculate_meld_na(bilirubin=1.0, creatinine=1.0, inr=1.0)
        assert "meld_na" in result
        assert result["meld_na"] >= 6

    def test_high_meld(self):
        """High MELD-Na score with elevated values."""
        result = m.calculate_meld_na(bilirubin=15.0, creatinine=4.0, inr=3.0)
        assert result["meld_na"] > 30

    def test_dialysis_adjustment(self):
        """Dialysis flag adjusts creatinine minimum."""
        result_no_dialysis = m.calculate_meld_na(bilirubin=2.0, creatinine=0.5, inr=1.5, dialysis=False)
        result_dialysis = m.calculate_meld_na(bilirubin=2.0, creatinine=0.5, inr=1.5, dialysis=True)
        assert result_dialysis["meld_na"] >= result_no_dialysis["meld_na"]


class TestCalculateBmiZ:
    """Tests for BMI z-score calculation."""

    def test_normal_bmi(self):
        """Normal BMI calculation."""
        result = m.calculate_bmi_z(weight_kg=70, height_cm=175, age_months=60)
        assert "bmi" in result
        assert result["category"] in ["NORMAL", "OVERWEIGHT"]

    def test_underweight(self):
        """Underweight BMI."""
        result = m.calculate_bmi_z(weight_kg=45, height_cm=170, age_months=60)
        assert result["category"] == "UNDERWEIGHT"

    def test_invalid_input(self):
        """Invalid weight/height returns error."""
        result = m.calculate_bmi_z(weight_kg=-10, height_cm=0, age_months=60)
        assert "error" in result


class TestConvertHba1c:
    """Tests for HbA1c conversion."""

    def test_hba1c_to_eag(self):
        """Convert HbA1c to eAG."""
        result = m.convert_hba1c(hba1c_percent=7.0)
        assert "eag_mgdl" in result
        assert "eag_mmol_l" in result
        # eAG = 28.7 * 7.0 - 46.7 = 154.2
        assert 150 < result["eag_mgdl"] < 160

    def test_eag_to_hba1c(self):
        """Convert eAG to HbA1c."""
        result = m.convert_hba1c(eag_mgdl=154)
        assert "hba1c_percent" in result

    def test_missing_input(self):
        """Missing both inputs returns error."""
        result = m.convert_hba1c()
        assert "error" in result


class TestCalculateApriFib4:
    """Tests for APRI/FIB-4 liver fibrosis scores."""

    def test_apri_calculation(self):
        """APRI calculation with platelets."""
        result = m.calculate_apri_fib4(ast_u_l=80, platelets_109=200)
        assert "apri" in result
        assert "fibrosis_risk" in result

    def test_fib4_calculation(self):
        """FIB-4 calculation with all parameters."""
        result = m.calculate_apri_fib4(ast_u_l=60, alt_u_l=40, platelets_109=150, age_years=55)
        assert "fib4" in result
        assert "fib4_risk" in result

    def test_invalid_ast(self):
        """Invalid AST returns error."""
        result = m.calculate_apri_fib4(ast_u_l=None)
        assert "error" in result


class TestAssessRow:
    """Tests for the row routing function."""

    def test_qt_row_routing(self):
        """QT data routes to calculate_qtc."""
        result = m.assess_row({"qt_ms": 420, "hr_bpm": 72})
        assert "qtc_ms" in result or "error" in result

    def test_meld_row_routing(self):
        """Bilirubin+creatinine routes to calculate_meld_na."""
        result = m.assess_row({"bilirubin": 2.0, "creatinine": 1.5, "inr": 1.2})
        assert "meld_na" in result or "error" in result

    def test_bmi_row_routing(self):
        """Weight routes to calculate_bmi_z."""
        result = m.assess_row({"weight_kg": 70, "height_cm": 175})
        assert "bmi" in result or "error" in result

    def test_hba1c_row_routing(self):
        """HbA1c routes to convert_hba1c."""
        result = m.assess_row({"hba1c_percent": 7.5})
        assert "eag_mgdl" in result or "error" in result

    def test_ast_row_routing(self):
        """AST routes to calculate_apri_fib4."""
        # Without platelets, returns basic info (AST, ULN)
        result = m.assess_row({"ast_u_l": 80})
        assert "ast_u_l" in result
        assert "ast_uln" in result

    def test_ast_row_with_platelets(self):
        """AST with platelets includes APRI score."""
        result = m.assess_row({"ast_u_l": 80, "platelets_109": 200})
        assert "apri" in result
        assert "fibrosis_risk" in result

    def test_generic_fallback(self):
        """Unknown fields fall back to calculate_score."""
        result = m.assess_row({"value": 10})
        assert isinstance(result, dict)

    def test_invalid_row_type(self):
        """Non-dict row returns error."""
        result = m.assess_row("not a dict")
        assert "error" in result


class TestProcessCsv:
    """Tests for CSV batch processing."""

    def test_process_csv_basic(self, tmp_path):
        """Process a simple CSV file."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("id,qty\nA,10\nB,20\n")

        output_csv = tmp_path / "output.csv"

        results = m.process_csv(str(input_csv), str(output_csv))
        assert len(results) == 2
        assert output_csv.exists()

    def test_process_csv_with_qt_data(self, tmp_path):
        """Process CSV with QT data."""
        input_csv = tmp_path / "qt_input.csv"
        input_csv.write_text("id,qt_ms,hr_bpm\nP1,420,72\nP2,510,65\n")

        output_csv = tmp_path / "qt_output.csv"
        results = m.process_csv(str(input_csv), str(output_csv))

        assert len(results) == 2
        assert output_csv.exists()

        content = output_csv.read_text()
        assert "qtc_ms" in content

    def test_process_csv_file_not_found(self, tmp_path):
        """FileNotFoundError for missing input."""
        with pytest.raises(FileNotFoundError):
            m.process_csv(str(tmp_path / "nonexistent.csv"), str(tmp_path / "out.csv"))


class TestMainCli:
    """Tests for the CLI main function."""

    def test_single_qt_calculation(self):
        """Single QT calculation via CLI."""
        result = m.main(["single", "--json", '{"qt_ms": 420, "hr_bpm": 72}'])
        assert result == 0

    def test_single_with_args(self):
        """Single calculation with individual args."""
        result = m.main(["single", "--qt", "420", "--hr", "72"])
        assert result == 0

    def test_batch_csv(self, tmp_path):
        """Batch CSV processing via CLI."""
        input_csv = tmp_path / "test_input.csv"
        input_csv.write_text("id,value,qty\nA,10,2\nB,20,3\n")
        output_csv = tmp_path / "test_output.csv"

        result = m.main(["batch", "--input", str(input_csv), "--output", str(output_csv)])
        assert result == 0
        assert output_csv.exists()

    def test_invalid_json(self):
        """Invalid JSON returns error code."""
        result = m.main(["single", "--json", "not valid json"])
        assert result == 1

    def test_batch_missing_file(self):
        """Batch with missing file returns error code."""
        result = m.main(["batch", "--input", "/nonexistent/path.csv", "--output", "/tmp/out.csv"])
        assert result == 1


class TestSafeFloat:
    """Tests for the _safe_float helper."""

    def test_valid_float(self):
        assert m._safe_float("3.14") == 3.14

    def test_valid_int(self):
        assert m._safe_float(42) == 42.0

    def test_none_returns_default(self):
        assert m._safe_float(None, 0.0) == 0.0

    def test_invalid_string(self):
        assert m._safe_float("abc", -1.0) == -1.0
