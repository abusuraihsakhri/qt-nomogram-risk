# QT Nomogram Risk

Educational browser-based QT correction calculator and Python research toolkit.

**Clinical limitation:** This implementation calculates Bazett and Fridericia corrected QT intervals. It does **not** implement the Chan/Isbister QT–heart-rate nomogram, estimate individual torsades de pointes probability, or constitute validated clinical decision-support software. Bazett QTc ≥500 ms is a screening threshold, **not** the Chan nomogram risk boundary. Do not use it as the sole basis for clinical decisions.

## Browser application

Open [the standalone calculator](web/) when serving the repository locally. GitHub Pages deployment is configured from the production branch, but a public live link will be added only after independent verification.

Enter measured QT (ms) and heart rate (bpm), click **Calculate QTc**, and review Bazett and Fridericia results. The prefilled 420-ms/72-bpm case is illustrative. **Copy JSON** copies the computed values. This standalone page does not make network requests or submit patient data; calculations execute locally in the browser. Do not enter identifying information.

## Python usage

Python 3.10+ is required. Install and test:

~~~bash
python -m pip install -e ".[dev]"
python -m pytest -q
node --check web/app.js
node --test web/app.test.js
~~~

CLI examples:

~~~bash
qt-nomogram-risk single --qt 420 --hr 72
qt-nomogram-risk single --json '{"qt_ms":420,"hr_bpm":72}'
python -m qt_nomogram batch --input sample.csv --output results.csv
~~~

Python API:

~~~python
from qt_nomogram import calculate_qtc
result = calculate_qtc(qt_ms=420, hr_bpm=72)
# Bazett QTc: 460.1 ms; nomogram_assessed=False; at_risk=None
~~~

Batch rows also support historical MELD-Na, HbA1c/eAG conversion, BMI, and APRI/FIB-4. Unknown schemas return an error rather than a fabricated score. **Historical MELD-Na is not MELD 3.0** and should not be used for contemporary transplant allocation. **Pediatric BMI z-scores and percentiles are not computed**, because validated age/sex growth-reference tables are not included.

## Local API and legacy audit tools

~~~bash
qt-nomogram-audit serve --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/qt -H "Content-Type: application/json" -d '{"qt_ms":420,"hr_bpm":72}'
~~~

The separate legacy commands audit, chat, batch, and verify-audit demonstrate rule-based worker logic. Their thresholds and simulated chat output are **not validated clinical standards or medical analysis**.

For externally accessible API use, configure two independent cryptographically strong secrets. Docker Compose requires both and binds the published port to localhost:

~~~bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(40))')"
export API_ACCESS_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(40))')"
docker compose up --build
~~~

When configured, API endpoints require an Authorization header containing a Bearer token. Audit-log reads are disabled unless a token is configured. The audit log is process-local, in memory, and verifies its HMAC signature chain against the current process key. Identifier patterns are screened, but regex screening is **not sufficient to guarantee de-identification or HIPAA compliance**. Do not submit real patient identifiers.

## Browser and deployment

Serve locally using python -m http.server 8080 and open http://127.0.0.1:8080/. The interface uses HTML, CSS, and vanilla JavaScript, with no external runtime dependencies, and targets current Chromium, Firefox, and Safari. The GitHub Actions matrix tests Python 3.10–3.13 and JavaScript arithmetic. Deployment and browser end-to-end behavior require verification after publishing.

## References

- Chan A et al. *QJM*. 2007;100:609–615. [doi:10.1093/qjmed/hcm072](https://doi.org/10.1093/qjmed/hcm072).
- Isbister GK, Page CB. *Br J Clin Pharmacol*. 2013;76:48–57. [doi:10.1111/bcp.12040](https://doi.org/10.1111/bcp.12040).

## License

[MIT](LICENSE).
