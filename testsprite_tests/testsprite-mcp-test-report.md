
# TestSprite AI Testing Report (MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** AgriSense
- **Date:** 2026-05-13
- **Prepared by:** TestSprite AI Team
- **Test Scope:** Full Backend API + Frontend (Codebase)
- **Server:** Flask dev server on port 5000

---

## 2️⃣ Requirement Validation Summary

### Requirement: Health Check & System Status
- **Description:** API health endpoint returns service status, loaded models, and weather API configuration.

#### Test TC001 — Health Check API Response Validation
- **Test Code:** [TC001_healthcheckapiresponsevalidation.py](./TC001_healthcheckapiresponsevalidation.py)
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/36f51564-34c4-4a4a-9c86-993a5ef5b710)
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** The `/api/health` endpoint returns correct status (`ok`), lists all 3 ML models (crop, yield, price), reports crop count, and accurately reflects the weather API configuration state. Response structure is well-formed.

---

### Requirement: Crop Data Access
- **Description:** API provides a list of all supported crops with metadata (icon, seasons, farming insights).

#### Test TC002 — Crop Listing Retrieval
- **Test Code:** [TC002_croplistingretrieval.py](./TC002_croplistingretrieval.py)
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/b19366b9-52ef-4f93-83ca-08917a0f0fc5)
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** The `/api/crops` endpoint returns all crops from the label encoder with correct metadata structure. Crop names, icons, seasons, and insights are populated from the CROP_META dictionary.

---

### Requirement: Crop Prediction (ML-Powered)
- **Description:** Accepts soil/weather parameters and returns crop recommendation, yield estimate, and price prediction using trained ML models.

#### Test TC003 — Crop Prediction with Valid Input
- **Test Code:** [TC003_croppredictionvalidinput.py](./TC003_croppredictionvalidinput.py)
- **Test Error:**
```
AssertionError: Top3 prediction missing keys: {'icon', 'insight', 'name', 'seasons'}
```
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/57871a48-de23-4f8d-b091-39d62f145b18)
- **Status:** ❌ Failed
- **Severity:** MEDIUM
- **Analysis / Findings:** The prediction endpoint works correctly for primary crop recommendation, but the `top3` array only contains `crop` (name) and `probability` fields — it does **not** include `icon`, `insight`, `name`, or `seasons` metadata. The test expected enriched top3 entries. This is a minor schema discrepancy: the top3 results use a simpler schema than the main `crop` field. **Recommendation:** Either enrich the `top3` response to include full crop metadata, or update the test expectation to match the simpler `{crop, probability}` schema.

#### Test TC004 — Crop Prediction with Weather Auto-fill
- **Test Code:** [TC004_croppredictionweatherautofill.py](./TC004_croppredictionweatherautofill.py)
- **Test Error:**
```
AssertionError
```
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/a1eaa438-6f2a-4d8b-ab49-a9f49a65ebf4)
- **Status:** ❌ Failed
- **Severity:** MEDIUM
- **Analysis / Findings:** When `use_weather: true` and `city` are provided, the server fetches live weather and merges temperature/humidity/rainfall into the prediction inputs. The test failed likely due to assertion on the response structure after weather merge. The `inputs` field in the response contains the validated numeric values but does not include `city` as a key, which the test may have expected. The weather data is returned separately in the `weather` field. **Recommendation:** Verify whether the test expected `city` in the `inputs` dict or the `weather` field.

#### Test TC005 — Crop Prediction Invalid Content-Type
- **Test Code:** [TC005_croppredictioninvalidcontenttype.py](./TC005_croppredictioninvalidcontenttype.py)
- **Test Error:**
```
AssertionError
```
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/99b59d0c-f1f3-4a0e-b5bf-8554c4538264)
- **Status:** ❌ Failed
- **Severity:** LOW
- **Analysis / Findings:** The server correctly rejects non-JSON requests to `/api/predict`, but the specific error response format or HTTP status code may differ from test expectations. Flask's `request.is_json` check returns a 400 with `{"error": "Content-Type must be application/json"}`. The test assertion failure suggests a mismatch in expected status code or error message format. **Recommendation:** Review the test to ensure it checks for status 400 and the exact error message string.

#### Test TC006 — Crop Prediction Validation Errors
- **Test Code:** [TC006_croppredictionvalidationerrors.py](./TC006_croppredictionvalidationerrors.py)
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/b559c57c-92c0-4d4b-b21a-81a27174779d)
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** Input validation works correctly. Out-of-range values, missing fields, and non-numeric inputs all produce appropriate 422 responses with descriptive error messages. The validation boundary checks (N: 0-140, P: 0-145, K: 0-205, pH: 3.5-9.5, etc.) function as designed.

---

### Requirement: Weather Data Integration
- **Description:** Fetches live weather data from OpenWeatherMap and provides farming-specific advisories.

#### Test TC007 — Weather Data Fetch
- **Test Code:** [TC007_weatherdatafetch.py](./TC007_weatherdatafetch.py)
- **Test Error:**
```
AssertionError: 'rainfall' key missing in weather data
```
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/1f0bd179-8760-4c4f-96ae-0a335fc1407f)
- **Status:** ❌ Failed
- **Severity:** MEDIUM
- **Analysis / Findings:** The `/api/weather` endpoint returns weather data under the key `rainfall_mm` (not `rainfall`). The test expected a `rainfall` key. This is a naming inconsistency — the `fetch_weather()` function uses `rainfall_mm` while other parts of the code (autofill) map it to `rainfall`. **Recommendation:** Standardize the field name across all endpoints, or update the test to check for `rainfall_mm`.

#### Test TC008 — Weather Data Auto-fill Fetch
- **Test Code:** [TC008_weatherdataautofillfetch.py](./TC008_weatherdataautofillfetch.py)
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/832ac31b-af33-4494-8c55-3c81230fa56a)
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** The `/api/weather/autofill` endpoint correctly transforms weather data into form-friendly values. The `autofill` object returns `temperature`, `humidity`, and `rainfall` fields mapped from the raw weather data. The `display` object provides additional UI context like condition, description, icon URL, wind speed, etc.

---

### Requirement: Prediction History
- **Description:** In-memory storage and retrieval of recent prediction results.

#### Test TC009 — Prediction History Retrieval
- **Test Code:** [TC009_predictionhistoryretrieval.py](./TC009_predictionhistoryretrieval.py)
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/04ae37ec-aab9-4a05-bbca-fe6153e4812f)
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** The `/api/history` endpoint correctly returns recent predictions with configurable `limit` parameter (default 50, max 100). History is ordered newest-first and includes all prediction details.

---

### Requirement: User Feedback
- **Description:** Accepts user feedback on prediction accuracy for future model improvement.

#### Test TC010 — User Feedback Submission
- **Test Code:** [TC010_userfeedbacksubmission.py](./TC010_userfeedbacksubmission.py)
- **Test Visualization and Result:** [View on TestSprite](https://www.testsprite.com/dashboard/mcp/tests/6bf78427-5075-489c-b9a3-def3c1fd967a/7921e673-f175-43dd-a37b-7d9ba7c67f2b)
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** The `/api/feedback` endpoint correctly accepts prediction_id with optional `correct` and `actual_crop` fields. Returns 422 when prediction_id is missing. Feedback is logged server-side for review.

---

## 3️⃣ Coverage & Matching Metrics

- **60%** of tests passed (6 out of 10)

| Requirement                    | Total Tests | ✅ Passed | ❌ Failed |
|-------------------------------|-------------|-----------|-----------|
| Health Check & System Status  | 1           | 1         | 0         |
| Crop Data Access              | 1           | 1         | 0         |
| Crop Prediction (ML-Powered)  | 4           | 1         | 3         |
| Weather Data Integration      | 2           | 1         | 1         |
| Prediction History            | 1           | 1         | 0         |
| User Feedback                 | 1           | 1         | 0         |

### Endpoint Coverage

| Endpoint                     | Tested | Status    |
|-----------------------------|--------|-----------|
| `GET /api/health`           | ✅     | Passing   |
| `GET /api/crops`            | ✅     | Passing   |
| `POST /api/predict`         | ✅     | Mixed (1/4 pass) |
| `GET /api/weather`          | ✅     | Failing   |
| `GET /api/weather/autofill` | ✅     | Passing   |
| `GET /api/history`          | ✅     | Passing   |
| `POST /api/feedback`        | ✅     | Passing   |
| `GET /api/mandi`            | ❌     | Not tested |

---

## 4️⃣ Key Gaps / Risks

> **60% of tests passed fully.**

### 🔴 Critical Issues
1. **Field Naming Inconsistency (`rainfall` vs `rainfall_mm`):** The `/api/weather` endpoint returns `rainfall_mm`, but the autofill endpoint maps it to `rainfall`. This inconsistency causes test failures and could confuse frontend consumers. **Fix:** Standardize to `rainfall_mm` everywhere or add an alias.

2. **Top3 Predictions Schema Mismatch:** The `top3` array in prediction results only has `{crop, probability}` while the primary prediction has full metadata `{name, icon, insight, seasons}`. Tests expected enriched top3 data. **Fix:** Enrich top3 entries with crop metadata from `CROP_META`.

### 🟡 Medium Risks
3. **Weather Auto-fill Prediction Integration:** The weather merge in `/api/predict` works, but the response schema doesn't explicitly include the city in `inputs`, causing assertion failures in integration tests.

4. **Content-Type Validation:** The error response format for non-JSON requests may not match client expectations in all cases.

### 🔵 Coverage Gaps
5. **`/api/mandi` endpoint is untested.** This external API integration (Indian government market prices) has no test coverage.

6. **No frontend UI tests were executed.** Only backend API tests ran. Frontend interaction tests (form submission, weather auto-fill UI, prediction display) should be added.

7. **No load/stress testing.** In-memory prediction history (capped at 100) is untested under concurrent access.

8. **No security testing.** API has no authentication, rate limiting, or input sanitization beyond basic validation. The hardcoded Mandi API key in source code is a security concern.

---
