# Backend Details

## 1. Project Structure

```
backend/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py               
│   └── project_analysis_agent.py   
│
├── tools/
│   ├── __init__.py
│   ├── kmz_parser.py               
│   ├── geospatial.py               
│   └── generate_mock_data.py       
│
├── api/
│   ├── __init__.py
│   ├── main.py                     
│   └── schemas.py                  
│
├── data/
│   ├── reference/                  
│   └── sample_claims/              
│
├── tests/
│   └── test_analyze.py             
│
├── requirements.txt
├── .env.example
```

---

## 2. Setup & Running Locally

### Step 1 — Install dependencies
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

### Step 2 — Generate mock data
```bash
python tools/generate_mock_data.py
```
### Step 3 — Start the server 
```bash
uvicorn api.main:app --reload --port 8000
```

### Step 4 — Run all tests 

```bash
# In a second terminal (server must be running)
python tests/test_analyze.py
```

---

## 3. Component Deep-Dive

### 3.1 BaseAgent

**Key methods:**

`_call_llm(user_input, json_mode=True)` — Calls the LLM with the agent's system prompt. Retries up to `max_retries` times with exponential backoff. JSON mode is enabled for OpenAI (forces valid JSON output). For Groq, JSON compliance is enforced through the system prompt instead.

`_parse_json(raw)` — Safely parses the LLM's response. Handles the common case where models wrap output in markdown code fences (` ```json ... ``` `) even when asked not to.

`_build_prompt(**kwargs)` — Formats a structured prompt from keyword arguments. Each kwarg becomes a labeled section. Dicts are pretty-printed as JSON.

```python
self._build_prompt(
    company_text_claim="500 ha forest in Karnataka",
    geospatial_analysis={"overlap_percent": 85.2, ...}
)
```
---

### 3.2 KMZ Parser

Handles reading KMZ files.


**`parse_kmz(kmz_path) → GeoDataFrame`**

1. Unzips the KMZ to a temp directory and finds the `.kml` file.
2. Reads all KML layers (companies sometimes split features across layers)
3. Drops null geometries
4. Sets CRS to EPSG:4326 (WGS84 — standard lat/lon)
5. Returns combined GeoDataFrame

**`get_utm_zone_crs(gdf) → str`**

India spans 68°E to 97°E, covering 4 UTM zones. Using the wrong zone gives incorrect area calculations. This function reads the centroid longitude and returns the correct EPSG code:

| Longitude Range | UTM Zone | EPSG | Covers |
|---|---|---|---|
| 66–72°E | Zone 42N | EPSG:32642 | Rajasthan west, Gujarat west |
| 72–78°E | Zone 43N | EPSG:32643 | Gujarat, Maharashtra, MP, Karnataka |
| 78–84°E | Zone 44N | EPSG:32644 | UP, AP, Odisha, Tamil Nadu |
| 84–90°E | Zone 45N | EPSG:32645 | West Bengal, Bihar |
| 90–96°E | Zone 46N | EPSG:32646 | Assam, Meghalaya, Arunachal |

**`get_area_hectares(gdf) → float`**

Reprojects to correct UTM zone, computes area in m², divides by 10,000 for hectares. Never uses EPSG:4326 for area — degrees are not meters and give meaningless numbers.

**`get_bounding_box(gdf) → dict`**

Returns `{min_lon, min_lat, max_lon, max_lat}` in WGS84. Used by the geospatial tool to query only the relevant slice of reference data, and later by the satellite agent for NDVI queries.

---

### 3.3 Geospatial Tool — `tools/geospatial.py`

The spatial comparison engine. Compares company claimed polygons against verified India reference data.

**`load_reference(bbox, layer) → GeoDataFrame`**

Smart loader with two paths:

```
POSTGIS_URL set?
    YES → Query PostGIS with ST_Intersects(bbox) → loads only relevant polygons
    NO  → Load full GeoJSON from disk → clip to bbox in memory
```

Available layers: `forest_cover`, `protected_areas`, `lulc`

**`compare_claim_to_reference(company_gdf, reference_gdf) → dict`**

Core comparison logic:

1. Reprojects both GeoDataFrames to the same UTM CRS
2. Dissolves all polygons into single shapes with `unary_union`
3. Computes geometric intersection
4. Calculates claimed hectares, verified hectares, overlap percentage
5. Raises flags based on thresholds:
   - `overlap < 10%` → CRITICAL flag
   - `overlap < 50%` → WARNING flag
   - `claimed > verified * 1.5` → overclaim flag

```python
# Returns:
{
    "claimed_hectares": 500.0,
    "verified_hectares": 423.5,
    "overlap_percent": 84.7,
    "utm_crs_used": "EPSG:32643",
    "flags": []
}
```

**`check_protected_area_overlap(company_gdf, protected_gdf) → dict`**

Cross-checks the company's polygon against India's protected areas (National Parks, Wildlife Sanctuaries, Tiger Reserves). Any overlap is an automatic disqualifier — land already under legal protection cannot generate new carbon credits. Returns the overlapping area in hectares and names of affected protected areas.

---

### 3.4 ProjectAnalysisAgent

**`run(kmz_path, company_text_claim) → dict`**

Six-step pipeline:

```
Step 1: parse_kmz(kmz_path)
        → GeoDataFrame of company's claimed polygons

Step 2: get_bounding_box() + get_area_hectares()
        → spatial metadata for downstream steps

Step 3: load_reference(bbox, "forest_cover")
        load_reference(bbox, "protected_areas")
        → reference GeoDataFrames, bbox-clipped

Step 4: compare_claim_to_reference()
        → overlap stats and area flags

Step 5: check_protected_area_overlap()
        → PA overlap stats and fraud flags

Step 6: _call_llm(structured prompt)
        → risk_level, trust_score, summary, red_flags
```

**Important:** Raw geo numbers (claimed_hectares, verified_hectares, overlap_percent) from the spatial tools **overwrite** whatever the LLM returns for those fields. The LLM cannot hallucinate the numbers — it only adds reasoning, risk classification, and the plain-English summary on top of verified geometry calculations.

**System prompt summary:**
The agent is instructed to act as a carbon credit verification expert specializing in Indian forestry. It receives the geospatial results as structured JSON and the company's text claim, and must return a verdict with `risk_level` (LOW/MEDIUM/HIGH/CRITICAL), `trust_score` (0–100), and flags/summary.

**Trust score logic (guided in prompt):**
- 60% weight: spatial overlap percentage
- 25% weight: consistency between text claim and geospatial result
- 15% weight: accuracy of claimed area vs verified area

---

### 3.5 FastAPI Server

**Files:** `api/main.py`, `api/schemas.py`

**Startup:** The `ProjectAnalysisAgent` is instantiated once on server startup (loading reference data into memory). This avoids re-loading GeoJSON on every request.

**`POST /analyze`**

Accepts `multipart/form-data`:

| Field | Type | Required | Description |
|---|---|---|---|
| `kmz_file` | File | Yes | Company's `.kmz` file |
| `company_claim` | String | No | Text description of the project |

Flow:
1. Validate file is `.kmz` and non-empty
2. Write to temp file (geopandas requires a real file path, not a stream)
3. Call `agent.run()`
4. Delete temp file in `finally` block
5. Return `AnalyzeResponse`

**`GET /health`**

Returns `{"status": "ok", "agent_ready": true}`. Used by the test suite to verify server is up before running scenarios.

**`AnalyzeResponse` schema (`api/schemas.py`):**

```python
{
    # Project identity (extracted by LLM)
    "project_name": str,
    "company_name": str,
    "state": str,              # Indian state
    "forest_type": str,

    # Hard geospatial numbers (never from LLM)
    "claimed_hectares": float,
    "verified_hectares": float,
    "overlap_percent": float,
    "protected_area_overlap_ha": float,

    # Verdict (from LLM reasoning)
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "trust_score": float,      # 0–100

    # Flags and explanation
    "all_flags": [str],
    "analysis_flags": [str],
    "red_flags": [str],
    "summary": str
}
```

---

## 4. API Reference

### `POST /analyze`

**Request:**
```bash
curl -X POST http://localhost:8000/analyze \
  -F "kmz_file=@data/sample_claims/valid_claim.kmz" \
  -F "company_claim=GreenFuture Ltd — 500 ha conservation in Kodagu, Karnataka"
```

**Response (200):**
```json
{
  "project_name": "GreenFuture Forest Conservation",
  "company_name": "GreenFuture Ltd",
  "state": "Karnataka",
  "forest_type": "Dense Evergreen",
  "claimed_hectares": 487.3,
  "verified_hectares": 421.8,
  "overlap_percent": 86.6,
  "protected_area_overlap_ha": 0.0,
  "risk_level": "LOW",
  "trust_score": 82.4,
  "all_flags": [],
  "analysis_flags": [],
  "red_flags": [],
  "summary": "The claimed forest area in Kodagu shows strong overlap with verified FSI forest cover data. No protected area conflicts detected. The project appears credible."
}
```

**Error responses:**
- `400` — File is not `.kmz` or is empty
- `422` — KMZ parsing failed (malformed file)
- `500` — Internal error (check server logs)

### `GET /health`

```bash
curl http://localhost:8000/health
# {"status": "ok", "agent_ready": true}
```

### Swagger UI

Interactive docs available at: `http://localhost:8000/docs`

---

## 5. Mock Data & Testing

### Generating Mock Data

```bash
python tools/generate_mock_data.py
```

Creates:

**Reference files** (in `data/reference/`):
- `india_forest_cover.geojson` — 15 forest polygons at real India locations (Western Ghats, Sundarbans, Simlipal, Nagarhole, Panna, etc.)
- `india_protected_areas.geojson` — 7 protected area polygons (Jim Corbett, Sundarbans NP, Nagarhole NP, etc.)

All mock polygons use real geographic coordinates at genuine forest/PA locations in India — just polygon shapes and sizes are approximate, not based on actual boundary surveys.

**Sample claim KMZ files** (in `data/sample_claims/`):

| File | Scenario | Expected Result |
|---|---|---|
| `valid_claim.kmz` | Polygon inside Western Ghats forest | Trust > 70, risk LOW/MEDIUM |
| `partial_claim.kmz` | Polygon half inside Nagarhole area, half outside | Trust 30–70, risk MEDIUM/HIGH |
| `invalid_claim.kmz` | Polygon placed in Thar Desert, claims "dense forest" | Trust < 30, risk HIGH/CRITICAL |
| `protected_overlap_claim.kmz` | Polygon inside Jim Corbett National Park | Protected area fraud flag |

---

## 6. Data Sourcing — India Specific

Replace mock data with real datasets, use these sources:

### Primary: Forest Survey of India (FSI)

**URL:** https://fsi.nic.in/forest-report-2023

The FSI publishes the **India State of Forest Report (ISFR)** every two years. The most recent edition (2023) contains district-level forest cover classified as:
- Very Dense Forest (canopy > 70%)
- Moderately Dense Forest (canopy 40–70%)
- Open Forest (canopy 10–40%)
- Scrub (canopy < 10%)
- Non-forest

GIS shapefiles are available via the FSI GIS portal — requires formal registration at fsi.nic.in. Once downloaded, convert to GeoJSON:

```bash
ogr2ogr -f GeoJSON data/reference/india_forest_cover.geojson \
  FSI_ForestCover_2023.shp -t_srs EPSG:4326
```

### Secondary: Bhuvan (ISRO)

**URL:** https://bhuvan.nrsc.gov.in

India's national geoportal run by ISRO/NRSC. Free after registration. Most useful layers:

- **LULC 2022-23** — Land Use Land Cover at 1:50,000 scale, derived from IRS satellite imagery. Covers forest, scrubland, wasteland, agricultural land
- **Wasteland Atlas** — Identifies degraded/barren land (critical for the Baseline Agent — was this forest before the project started?)

Download as KML or shapefile, convert with `ogr2ogr`.

### Protected Areas: Protected Planet

**URL:** https://www.protectedplanet.net/country/IND

No registration required. Direct KML/shapefile download for all of India's protected areas. This is what loads into the `protected_areas` table/file.

India has 900+ protected areas including:
- 106 National Parks
- 567 Wildlife Sanctuaries
- 53 Tiger Reserves
- 18 Biosphere Reserves

Any carbon credit claim polygon overlapping any of these is automatically fraudulent — the land is already legally protected and cannot be newly credited.

### Carbon Registries (for fraud cross-check)

| Registry | URL | Use |
|---|---|---|
| Verra VCS | registry.verra.org | Search India projects — check if area already registered |
| Gold Standard | registry.goldstandard.org | Same |
| India BEE PAT | beeindia.gov.in | India-specific energy efficiency credits |

A company claiming credits for land already registered on Verra is double-counting fraud.

### Satellite / NDVI Data (for future SatelliteAgent)

| Source | Access | Best For |
|---|---|---|
| Sentinel-2 (Copernicus) | Free API key | NDVI, recent imagery, 10m resolution |
| Landsat (USGS) | Free | Historical baseline from 2000 onwards |
| Google Earth Engine | Free (research) | Best for India-wide analysis, Python API |
| Bhuvan NRSC API | Free | IRS satellite data, India-specific |

NDVI thresholds for India's forest types:
- Dense forest: `NDVI > 0.6`
- Moderately dense: `0.4–0.6`
- Open forest/scrub: `0.2–0.4`
- Non-forest/degraded: `< 0.2`

---

## 7. Storage Architecture — PostGIS

**The PostGIS solution:**

PostGIS is PostgreSQL with geospatial extensions. It stores your forest polygons in a database with a **spatial GIST index** — a structure that makes bounding box queries extremely fast.

```
Company submits claim in Karnataka (bbox: 74°E–78°E, 11°N–15°N)
        ↓
PostGIS ST_Intersects query with that bbox
        ↓
Spatial index jumps directly to Karnataka polygons
        ↓
~50KB of data loaded, not 2GB
```

**The `load_reference()` function in `geospatial.py` handles this automatically:**


No code changes needed to switch — just set the environment variable.

---

## 8. PostGIS Setup

### Quick start with Docker

```bash
docker run -d \
  --name proofofcarbon-db \
  -e POSTGRES_USER=poc \
  -e POSTGRES_PASSWORD=poc_secret \
  -e POSTGRES_DB=proofofcarbon \
  -p 5432:5432 \
  postgis/postgis:15-3.4
```

Add to `.env`:
```env
POSTGIS_URL=postgresql://poc:poc_secret@localhost:5432/proofofcarbon
```

### Create tables

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE forest_cover (
    id               SERIAL PRIMARY KEY,
    name             TEXT,
    forest_type      TEXT,
    state            TEXT,
    ndvi_mean        FLOAT,
    canopy_cover_pct FLOAT,
    source           TEXT,
    verified_year    INT,
    geom             GEOMETRY(MULTIPOLYGON, 4326)
);

CREATE TABLE protected_areas (
    id      SERIAL PRIMARY KEY,
    name    TEXT,
    type    TEXT,
    state   TEXT,
    wdpa_id TEXT,
    geom    GEOMETRY(MULTIPOLYGON, 4326)
);

-- Critical: spatial indexes enable fast bbox queries
CREATE INDEX idx_forest_cover_geom ON forest_cover USING GIST(geom);
CREATE INDEX idx_protected_areas_geom ON protected_areas USING GIST(geom);
```

### Load data

```bash
# From FSI shapefile
ogr2ogr -f "PostgreSQL" \
  PG:"host=localhost dbname=proofofcarbon user=poc password=poc_secret" \
  FSI_ForestCover_2023.shp -nln forest_cover -t_srs EPSG:4326

# From mock GeoJSON (to test PostGIS path)
ogr2ogr -f "PostgreSQL" \
  PG:"host=localhost dbname=proofofcarbon user=poc password=poc_secret" \
  data/reference/india_forest_cover.geojson -nln forest_cover -t_srs EPSG:4326

ogr2ogr -f "PostgreSQL" \
  PG:"host=localhost dbname=proofofcarbon user=poc password=poc_secret" \
  data/reference/india_protected_areas.geojson -nln protected_areas -t_srs EPSG:4326
```

### Verify

```sql
SELECT COUNT(*) FROM forest_cover;

-- Test Karnataka bbox
SELECT name, forest_type FROM forest_cover
WHERE ST_Intersects(geom, ST_MakeEnvelope(74.0, 11.0, 78.5, 15.5, 4326));
```

---