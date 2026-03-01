"""
api/main.py — FastAPI server exposing /analyze endpoint.
"""

import logging
import os
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import AnalyzeResponse, HealthResponse
from agents.project_analysis import ProjectAnalysisAgent
from agents.satellite_evidence import SatelliteEvidenceAgent

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ProofOfCarbon API",
    description="AI-powered carbon credit verification for India",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents once at startup
project_agent: ProjectAnalysisAgent | None = None
satellite_agent: SatelliteEvidenceAgent | None = None


@app.on_event("startup")
async def startup():
    global project_agent, satellite_agent
    logger.info("Initializing ProjectAnalysisAgent...")
    project_agent = ProjectAnalysisAgent()
    logger.info("Initializing SatelliteEvidenceAgent...")
    satellite_agent = SatelliteEvidenceAgent()
    logger.info("All agents ready.")


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", agent_ready=project_agent is not None)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    kmz_file: UploadFile = File(
        ..., description="Company's KMZ file with claimed forest polygon"
    ),
    company_claim: str = Form(
        default="", description="Company's text description of the project"
    ),
):
    """
    Analyze a carbon credit claim.

    Pipeline:
      1. ProjectAnalysisAgent  — spatial overlap vs. reference forest data
      2. SatelliteEvidenceAgent — MODIS NDVI validation of forest cover

    Returns a merged verdict with trust score, risk level, flags, and satellite evidence.
    """
    if not kmz_file.filename.endswith(".kmz"):
        raise HTTPException(status_code=400, detail="File must be a .kmz file")

    content = await kmz_file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Write to temp file (geopandas needs a real file path)
    with tempfile.NamedTemporaryFile(suffix=".kmz", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # ── Stage 1: Spatial analysis ─────────────────────────────────────────
        spatial_result = project_agent.run(
            kmz_path=tmp_path, company_text_claim=company_claim
        )

        # ── Stage 2: Satellite evidence ───────────────────────────────────────
        bbox = spatial_result.get("bbox")  # set by ProjectAnalysisAgent
        satellite_result = {}
        if bbox and satellite_agent:
            try:
                satellite_result = satellite_agent.run(
                    bbox=bbox,
                    company_text_claim=company_claim,
                    project_analysis_result=spatial_result,
                )
            except Exception as sat_exc:
                logger.warning(f"SatelliteEvidenceAgent failed (non-fatal): {sat_exc}")

        # ── Stage 3: Merge results ────────────────────────────────────────────
        merged = {**spatial_result, **satellite_result}

        # Adjust trust score by satellite modifier (clamped 0-100)
        modifier = satellite_result.get("satellite_trust_modifier", 0)
        base_trust = float(spatial_result.get("trust_score", 50))
        merged["trust_score"] = max(0.0, min(100.0, base_trust + modifier))

        # Combine all flags into one list
        spatial_flags  = spatial_result.get("all_flags", [])
        sat_flags      = satellite_result.get("satellite_flags", [])
        merged["all_flags"] = spatial_flags + [
            f for f in sat_flags if f not in spatial_flags
        ]

        return AnalyzeResponse(**merged)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
    finally:
        os.unlink(tmp_path)
