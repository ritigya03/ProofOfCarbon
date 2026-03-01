"""
api/main.py — FastAPI server exposing /analyze endpoint.

Full pipeline (4 agents):
  1. ProjectAnalysisAgent   — spatial overlap vs. reference forest data
  2. SatelliteEvidenceAgent — MODIS NDVI validation of forest cover
  3. FraudDetectionAgent    — cross-signal fraud pattern analysis
  4. VerifierAgent          — final verdict aggregation
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
from agents.fraud_detection import FraudDetectionAgent
from agents.verifier import VerifierAgent

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ProofOfCarbon API",
    description="AI-powered carbon credit verification for India",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiated once at startup — reference data loaded into memory here
project_agent: ProjectAnalysisAgent | None = None
satellite_agent: SatelliteEvidenceAgent | None = None
fraud_agent: FraudDetectionAgent | None = None
verifier_agent: VerifierAgent | None = None


@app.on_event("startup")
async def startup():
    global project_agent, satellite_agent, fraud_agent, verifier_agent
    logger.info("Initializing ProjectAnalysisAgent...")
    project_agent = ProjectAnalysisAgent()
    logger.info("Initializing SatelliteEvidenceAgent...")
    satellite_agent = SatelliteEvidenceAgent()
    logger.info("Initializing FraudDetectionAgent...")
    fraud_agent = FraudDetectionAgent()
    logger.info("Initializing VerifierAgent...")
    verifier_agent = VerifierAgent()
    logger.info("All agents ready.")


@app.get("/health", response_model=HealthResponse)
def health():
    all_ready = all([project_agent, satellite_agent, fraud_agent, verifier_agent])
    return HealthResponse(status="ok", agent_ready=all_ready)


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
    Analyze a carbon credit claim through a 4-stage agent pipeline.

    Stage 1 — ProjectAnalysisAgent:  spatial overlap vs verified India forest data
    Stage 2 — SatelliteEvidenceAgent: NDVI vegetation check via MODIS
    Stage 3 — FraudDetectionAgent:   cross-signal fraud pattern detection
    Stage 4 — VerifierAgent:         final verdict + recommendation

    Stages 2-4 are non-fatal — if one fails, the pipeline continues with what it has.
    """
    if not kmz_file.filename.endswith(".kmz"):
        raise HTTPException(status_code=400, detail="File must be a .kmz file")

    content = await kmz_file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    with tempfile.NamedTemporaryFile(suffix=".kmz", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # ── Stage 1: Spatial analysis (required — fails hard if broken) ───────
        logger.info("--- Stage 1: ProjectAnalysisAgent ---")
        spatial_result = project_agent.run(
            kmz_path=tmp_path, company_text_claim=company_claim
        )
        merged = {**spatial_result}

        # ── Stage 2: Satellite evidence (non-fatal) ───────────────────────────
        logger.info("--- Stage 2: SatelliteEvidenceAgent ---")
        bbox = spatial_result.get("bbox")
        satellite_result = {}
        if bbox and satellite_agent:
            try:
                satellite_result = satellite_agent.run(
                    bbox=bbox,
                    company_text_claim=company_claim,
                    project_analysis_result=spatial_result,
                )
                merged.update(satellite_result)

                # Adjust trust score by satellite modifier
                modifier = float(satellite_result.get("satellite_trust_modifier", 0))
                base_trust = float(merged.get("trust_score", 50))
                merged["trust_score"] = max(0.0, min(100.0, base_trust + modifier))

                # Merge satellite flags into all_flags
                sat_flags = satellite_result.get("satellite_flags", [])
                merged["all_flags"] = merged.get("all_flags", []) + [
                    f for f in sat_flags if f not in merged.get("all_flags", [])
                ]
            except Exception as e:
                logger.warning(f"SatelliteEvidenceAgent failed (non-fatal): {e}")

        # ── Stage 3: Fraud detection (non-fatal) ──────────────────────────────
        logger.info("--- Stage 3: FraudDetectionAgent ---")
        fraud_result = {}
        if fraud_agent:
            try:
                fraud_result = fraud_agent.run(combined_data=merged)
                merged.update(fraud_result)

                # Merge fraud flags
                fraud_flags = fraud_result.get("fraud_flags", [])
                merged["all_flags"] = merged.get("all_flags", []) + [
                    f for f in fraud_flags if f not in merged.get("all_flags", [])
                ]
            except Exception as e:
                logger.warning(f"FraudDetectionAgent failed (non-fatal): {e}")

        # ── Stage 4: Final verdict (non-fatal) ────────────────────────────────
        logger.info("--- Stage 4: VerifierAgent ---")
        if verifier_agent:
            try:
                verdict_result = verifier_agent.run(combined_data=merged)
                merged.update(verdict_result)

                # VerifierAgent produces final_trust_score — make it the canonical trust_score
                if "final_trust_score" in verdict_result:
                    merged["trust_score"] = float(verdict_result["final_trust_score"])
                if "final_risk_level" in verdict_result:
                    merged["risk_level"] = verdict_result["final_risk_level"]
            except Exception as e:
                logger.warning(f"VerifierAgent failed (non-fatal): {e}")

        logger.info(
            f"Pipeline complete — verdict={merged.get('final_verdict', 'N/A')}, "
            f"trust={merged.get('trust_score')}, risk={merged.get('risk_level')}"
        )

        return AnalyzeResponse(**merged)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
    finally:
        os.unlink(tmp_path)
