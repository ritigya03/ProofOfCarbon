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

# Initialize agent once at startup (loads reference data)
agent = None


@app.on_event("startup")
async def startup():
    global agent
    logger.info("Initializing ProjectAnalysisAgent...")
    agent = ProjectAnalysisAgent()
    logger.info("Agent ready.")


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", agent_ready=agent is not None)


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
    Analyze a carbon credit claim by comparing the submitted KMZ
    against India reference forest data.

    Returns a trust score, risk classification, flags, and summary.
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
        result = agent.run(kmz_path=tmp_path, company_text_claim=company_claim)
        return AnalyzeResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
    finally:
        os.unlink(tmp_path)
