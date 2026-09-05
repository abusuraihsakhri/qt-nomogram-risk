# Qt Nomogram Risk

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Standards:** CAP / CLSI / ISO 15189

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-44%20Passed-brightgreen.svg)

</div>

---

## Overview

QT Nomogram Risk Stratifier implements the Chan QT nomogram for assessing torsades de pointes risk from QT interval and heart rate measurements. The system provides multiple clinical calculation modules including QTc correction, MELD-Na scoring, BMI z-scores, HbA1c conversion, and liver fibrosis indices (APRI/FIB-4).

---

## Features

### Clinical Calculation Modules

| Module | Function | Description |
|--------|----------|-------------|
| **QTc** | `calculate_qtc()` | Bazett's corrected QT interval with torsades risk zones |
| **MELD-Na** | `calculate_meld_na()` | Liver disease severity scoring |
| **BMI z-score** | `calculate_bmi_z()` | Body mass index with age-adjusted z-score |
| **HbA1c** | `convert_hba1c()` | Convert between HbA1c and estimated average glucose |
| **APRI/FIB-4** | `calculate_apri_fib4()` | Liver fibrosis risk indices |

### Enterprise Features

- **Zero-PHI Outbound Guard:** AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation
- **FastAPI REST API:** OpenAPI 3.1 endpoints with Prometheus metrics
- **Multi-worker Agent Architecture:** Specialized workers for QC, safety, and protocol conformance

---

## Installation

### Local Development

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/qt-nomogram-risk.git
cd qt-nomogram-risk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"
```

### Docker

```bash
docker build -t qt-nomogram-risk .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key qt-nomogram-risk
```

---

## Usage

### Command Line Interface

#### Single Calculation (QTc)

```bash
# Using JSON input
python -m qt_nomogram single --json '{"qt_ms": 420, "hr_bpm": 72}'

# Using individual arguments
python -m qt_nomogram single --qt 420 --hr 72
```

#### Batch CSV Processing

```bash
python -m qt_nomogram batch --input patients.csv --output results.csv
```

#### Enterprise CLI

```bash
# Run audit evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --critical

# Batch process records
python cli.py batch -i input.csv -o output.csv

# Verify audit trail integrity
python cli.py verify-audit

# Launch REST API server
python cli.py serve --host 127.0.0.1 --port 8000
```

### REST API

```bash
# Health check
curl http://localhost:8000/health

# Submit audit task
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"task_id": "TASK-001", "target_identifier": "KEY-01", "primary_metric": 28.5}'

# Get Prometheus metrics
curl http://localhost:8000/metrics
```

### Python API

```python
import qt_nomogram as m

# Calculate QTc
result = m.calculate_qtc(qt_ms=420, hr_bpm=72)
print(result)
# {'qt_ms': 420.0, 'rr_ms': 833.3, 'qtc_ms': 438.2, 'risk_zone': 'NORMAL', 'at_risk': False}

# Calculate MELD-Na
result = m.calculate_meld_na(bilirubin=2.0, creatinine=1.5, inr=1.2)
print(result)
# {'meld_na': 18, 'priority': 'LOW'}

# Process CSV file
results = m.process_csv("input.csv", "output.csv")
```

---

## Input Data Schema

### QTc Calculation

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `qt_ms` | float | Yes | QT interval in milliseconds |
| `hr_bpm` | float | No* | Heart rate in beats per minute |
| `rr_ms` | float | No* | RR interval in milliseconds |

*Either `hr_bpm` or `rr_ms` must be provided.

### MELD-Na Calculation

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bilirubin` | float | Yes | Serum bilirubin (mg/dL) |
| `creatinine` | float | Yes | Serum creatinine (mg/dL) |
| `inr` float | No | International normalized ratio |
| `sodium` | float | No | Serum sodium (mEq/L) |
| `dialysis` | bool | No | Dialysis in prior week |

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test module
pytest tests/test_qt_nomogram.py -v
```

---

## Security Configuration

### Audit Secret Key

The HMAC-SHA256 audit trail requires a secret key. Set the `AUDIT_SECRET_KEY` environment variable:

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Set environment variable
export AUDIT_SECRET_KEY="your-generated-key"
```

> **Warning:** Without `AUDIT_SECRET_KEY` set, a development key is used with a runtime warning. Always set this in production.

### PHI Protection

The system includes a Zero-PHI outbound guard that blocks:
- Medical Record Numbers (MRN)
- Social Security Numbers
- Phone numbers
- Email addresses
- Patient names (common patterns)

---

## Project Structure

```
qt-nomogram-risk/
├── agents/              # Enterprise agent architecture
│   ├── base.py          # Security, PHI guard, audit trail
│   ├── models.py        # Pydantic data models
│   ├── supervisor.py    # Multi-agent orchestrator
│   ├── workers.py       # Specialized evaluation workers
│   ├── api.py           # FastAPI REST endpoints
│   └── ...
├── tests/               # Test suite
├── qt_nomogram.py       # Core clinical calculations
├── cli.py               # Enterprise CLI
├── pyproject.toml       # Package configuration
├── Dockerfile           # Container build
└── docker-compose.yml   # Container orchestration
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
