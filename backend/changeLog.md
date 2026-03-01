# ProofOfCarbon — Changelog & Full-Stack Integration Guide

---

## What Was Built (Session Summary)

### Backend — Files Added

```
backend/
├── agents/
│   ├── base_agent.py               ← NEW: LLM client, retry logic, JSON parsing. Parent of all agents.
│   ├── project_analysis.py         ← NEW: Stage 1. Parses KMZ, runs spatial comparison, LLM verdict.
│   ├── satellite_evidence.py       ← NEW: Stage 2. Fetches NDVI, interprets vegetation class.
│   ├── fraud_detection.py          ← NEW: Stage 3. Cross-signal fraud pattern detection.
│   └── verifier.py                 ← NEW: Stage 4. Final verdict — VERIFIED / REJECTED / etc.
│
├── tools/
│   ├── kmz_parser.py               ← NEW: Unzips KMZ, reads KML, computes area in correct UTM zone.
│   ├── geospatial.py               ← NEW: Spatial overlap vs reference, protected area check, PostGIS/file loader.
│   └── generate_mock_data.py       ← NEW: Creates test KMZ files + India reference GeoJSON. Run once.
│
├── api/
│   ├── main.py                     ← NEW → UPDATED: FastAPI server. Now runs full 4-agent pipeline.
│   └── schemas.py                  ← NEW → UPDATED: Pydantic models. Added satellite, fraud, verifier fields.
│
├── data/
│   ├── reference/                  ← GENERATED: india_forest_cover.geojson, india_protected_areas.geojson
│   └── sample_claims/              ← GENERATED: valid/partial/invalid/protected_overlap .kmz files
│
├── tests/
│   ├── test_analyze.py             ← NEW → UPDATED: Integration test. Now checks all 4 pipeline stages.
│   ├── test_fraud_detection.py     ← NEW: Isolated unit test for FraudDetectionAgent.
│   └── test_verifier.py            ← NEW: Isolated unit test for VerifierAgent.
│
├── requirements.txt                ← NEW
├── .env.example                    ← NEW
└── POSTGIS_SETUP.md                ← NEW: Docker + SQL setup for production data storage.
```

### Key Decisions Made
- **Groq over OpenAI** for dev — free tier, no billing. `BaseAgent` auto-detects which key is present.
- **UTM zones** per polygon centroid — India spans 4 zones, wrong zone = wrong hectare numbers.
- **LLM numbers are never trusted** — hectares, overlap %, PA overlap always come from Shapely geometry tools and overwrite whatever the LLM returns.
- **PostGIS as the production data store** — India forest cover is 500MB–2GB uncompressed. PostGIS spatial indexes load only the bbox-relevant slice. Falls back to local GeoJSON when `POSTGIS_URL` is not set.
- **Stages 2–4 are non-fatal** — if satellite/fraud/verifier fail, the API still returns Stage 1 spatial results rather than a 500.

---

## The 4-Agent Pipeline

```
Company submits KMZ + text claim
            │
            ▼
┌─────────────────────────┐
│  Stage 1                │  project_analysis.py
│  ProjectAnalysisAgent   │  → parses KMZ polygon
│                         │  → compares to FSI reference forest data
│                         │  → checks protected area overlap
│                         │  → LLM assigns risk_level + trust_score
└────────────┬────────────┘
             │  passes: bbox, overlap_%, claimed_ha, verified_ha, flags
             ▼
┌─────────────────────────┐
│  Stage 2                │  satellite_evidence.py
│  SatelliteEvidenceAgent │  → fetches NDVI for the bbox
│                         │  → classifies vegetation (DENSE_FOREST → BARE_GROUND)
│                         │  → LLM interprets trend (INCREASING/STABLE/DECREASING)
│                         │  → outputs satellite_trust_modifier (-30 to +10)
└────────────┬────────────┘
             │  adjusts trust_score, adds satellite_flags
             ▼
┌─────────────────────────┐
│  Stage 3                │  fraud_detection.py
│  FraudDetectionAgent    │  → looks for phantom forest, area inflation,
│                         │    signal contradiction, PA laundering,
│                         │    round number anomaly, admin mismatch
│                         │  → outputs anomaly_score (0-100) + fraud_patterns
└────────────┬────────────┘
             │  adds fraud_flags
             ▼
┌─────────────────────────┐
│  Stage 4                │  verifier.py
│  VerifierAgent          │  → aggregates all signals (spatial 40%, satellite 30%, fraud 30%)
│                         │  → outputs final_verdict:
│                         │    VERIFIED / CONDITIONALLY_VERIFIED /
│                         │    REQUIRES_REVIEW / REJECTED
│                         │  → outputs recommendation for registry officer
└────────────┬────────────┘
             │
             ▼
      AnalyzeResponse (JSON)
      → frontend consumes this
```

---

## How Frontend Connects

The frontend is a **Next.js app** (App Router, TypeScript, Tailwind). It talks to the FastAPI backend over HTTP. There is no shared code between them — the contract is the `/analyze` JSON response.

### The connection in one diagram

```
[User uploads KMZ + types claim text]
            │
            ▼
  frontend/  (Next.js, port 3000)
  - File upload form component
  - POST /analyze to backend
            │
            ▼  multipart/form-data
  backend/   (FastAPI, port 8000)
  - Runs 4-agent pipeline
  - Returns AnalyzeResponse JSON
            │
            ▼
  frontend/
  - Renders trust score, verdict, flags, NDVI, fraud patterns
```

### CORS

Already configured in `api/main.py` — all origins allowed for dev:
```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```
For production, change `["*"]` to your frontend domain.

---

## Frontend Implementation Guide

### 1. Environment variable

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

In production:
```env
NEXT_PUBLIC_API_URL=https://your-backend-domain.com
```

### 2. The API call

The core fetch — put this in `frontend/lib/api.ts`:

```typescript
export interface AnalyzeResponse {
  // Identity
  project_name: string | null;
  company_name: string | null;
  state: string | null;
  forest_type: string | null;

  // Spatial (Stage 1)
  claimed_hectares: number;
  verified_hectares: number;
  overlap_percent: number;
  protected_area_overlap_ha: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  trust_score: number;
  summary: string;
  all_flags: string[];

  // Satellite (Stage 2)
  ndvi_current_mean: number | null;
  ndvi_trend: "INCREASING" | "STABLE" | "DECREASING" | null;
  vegetation_class: string | null;
  satellite_risk_level: string | null;
  satellite_trust_modifier: number | null;
  satellite_summary: string | null;
  satellite_flags: string[];

  // Fraud (Stage 3)
  anomaly_score: number | null;
  fraud_risk_level: string | null;
  fraud_patterns: Record<string, string> | null;
  fraud_flags: string[];
  fraud_summary: string | null;

  // Final verdict (Stage 4)
  final_verdict: "VERIFIED" | "CONDITIONALLY_VERIFIED" | "REQUIRES_REVIEW" | "REJECTED" | null;
  final_trust_score: number | null;
  confidence: "HIGH" | "MEDIUM" | "LOW" | null;
  key_findings: string[];
  recommendation: string | null;
  verification_summary: string | null;
}

export async function analyzeKmz(
  kmzFile: File,
  companyClaim: string
): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("kmz_file", kmzFile);
  form.append("company_claim", companyClaim);

  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/analyze`,
    { method: "POST", body: form }
  );

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Analysis failed");
  }

  return res.json();
}
```

### 3. What to display — component breakdown

The response maps cleanly to UI sections. Here's how to think about which fields go where:

**Upload form** — user-facing input:
```
[ KMZ file upload input        ]
[ Company claim textarea       ]
[ Submit button                ]
```
Fields sent: `kmz_file`, `company_claim`

---

**Trust score hero** — the first thing the user sees after analysis:
```
Fields: final_trust_score (or trust_score as fallback)
        final_verdict  → badge color
        confidence
        recommendation  → bold action text
```
Color logic:
```typescript
const verdictColor = {
  VERIFIED:                "green",
  CONDITIONALLY_VERIFIED:  "yellow",
  REQUIRES_REVIEW:         "orange",
  REJECTED:                "red",
}[result.final_verdict ?? "REQUIRES_REVIEW"];
```

---

**Spatial analysis card** (Stage 1):
```
Fields: claimed_hectares
        verified_hectares
        overlap_percent      → progress bar
        protected_area_overlap_ha
        state, forest_type
        summary
```

---

**Satellite evidence card** (Stage 2):
```
Fields: ndvi_current_mean    → gauge or number
        ndvi_trend           → ↑ ↓ → icon
        vegetation_class     → badge
        satellite_summary
```
Show only if `ndvi_current_mean !== null` — stage may not run if bbox fails.

---

**Fraud detection card** (Stage 3):
```
Fields: anomaly_score        → 0-100 risk meter
        fraud_patterns       → table of pattern → status
        fraud_summary
```
Pattern status colors:
```typescript
const patternColor = {
  CONFIRMED: "red",
  SUSPECTED: "orange",
  POSSIBLE:  "yellow",
  CLEAR:     "green",
}[status];
```

---

**Key findings + flags** (Stage 4 + all stages):
```
Fields: key_findings         → bulleted list
        all_flags            → warning badges
        verification_summary → final paragraph
```

### 4. Loading state

The pipeline takes 5–15 seconds (4 LLM calls in sequence). Show a progress indicator with stage labels:

```typescript
const stages = [
  "Analysing forest cover...",
  "Checking satellite data...",
  "Scanning for fraud patterns...",
  "Generating final verdict...",
];
```

You can poll `/health` while waiting, or just animate through the stage labels on a timer.

### 5. Error handling

```typescript
try {
  const result = await analyzeKmz(file, claim);
  setResult(result);
} catch (e) {
  // Backend returns { detail: "..." } on errors
  setError(e.message);
}
```

Common errors to surface to the user:
- `"File must be a .kmz file"` → wrong file type
- `"Failed to parse KMZ"` → malformed file
- `"Analysis error: ..."` → pipeline failure (check server logs)

---

## Running the Full Stack

```bash
# Terminal 1 — Backend
cd backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

Both must run simultaneously. The frontend calls the backend at port 8000.

---

## Quick Test Reference

```bash
# Generate mock data (run once)
cd backend
python tools/generate_mock_data.py

# Unit test individual agents (no server needed)
python tests/test_fraud_detection.py
python tests/test_verifier.py

# Full pipeline integration test (server must be running)
python tests/test_analyze.py
```

Test scenarios covered:

| File | What it tests | Expected verdict |
|---|---|---|
| `valid_claim.kmz` | Polygon inside Western Ghats | VERIFIED |
| `partial_claim.kmz` | Half inside Karnataka forest | CONDITIONALLY_VERIFIED / REQUIRES_REVIEW |
| `invalid_claim.kmz` | Polygon in Thar Desert, claims forest | REJECTED |
| `protected_overlap_claim.kmz` | Polygon inside Jim Corbett NP | REJECTED |

---

## What's Not Built Yet

| Component | Status | Notes |
|---|---|---|
| Blockchain audit trail | ⏳ Phase 5 | Hash report → store on Polygon Amoy |
| Real satellite data | ⏳ | Currently mocked. Wire to GEE or Sentinel Hub |
| PostGIS with real India data | ⏳ | See `POSTGIS_SETUP.md`. FSI + Bhuvan data needed |