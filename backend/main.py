from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agents.project_analysis import ProjectAnalysisAgent

app = FastAPI(title="ProofOfCarbon API", version="0.1.0")

# Allow requests from the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ──────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    report_text: str

# ── Agents ────────────────────────────────────────────────────────────────────

project_analysis_agent = ProjectAnalysisAgent()

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "ProofOfCarbon API is running"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    Run the Project Analysis Agent on a raw project report.
    Returns extracted structured data.
    """
    if not req.report_text.strip():
        raise HTTPException(status_code=400, detail="report_text cannot be empty")

    result = project_analysis_agent.run({"report_text": req.report_text})
    return result
