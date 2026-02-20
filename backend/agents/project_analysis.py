from agents.base_agent import Agent
from dotenv import load_dotenv
import os
import json

load_dotenv()

PROVIDER  = os.getenv("LLM_PROVIDER", "groq").lower()
API_KEY   = os.getenv("LLM_API_KEY")


def _call_llm(prompt: str) -> str:
    """Send a prompt to the configured LLM and return the text response."""
    if PROVIDER == "groq":
        from groq import Groq
        client = Groq(api_key=API_KEY)
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content

    elif PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content

    else:
        raise ValueError(f"Unsupported LLM provider: {PROVIDER}")


class ProjectAnalysisAgent(Agent):
    """
    Agent 1 — Project Analysis
    Extracts structured information from a raw carbon credit project report.
    """

    def __init__(self):
        super().__init__(name="ProjectAnalysisAgent")

    def run(self, input_data: dict) -> dict:
        """
        Args:
            input_data: { "report_text": str }

        Returns:
            {
                "project_name": str,
                "location": str,
                "timeline": str,
                "claimed_reduction_tco2": float | None,
                "methodology": str,
                "summary": str
            }
        """
        report_text = input_data.get("report_text", "")

        prompt = f"""
You are a carbon credit audit assistant. Analyze the following carbon credit project report and extract key information.

Return ONLY a valid JSON object with these fields:
- project_name: string
- location: string (country / region)
- timeline: string (e.g., "2020–2030")
- claimed_reduction_tco2: number (tonnes of CO2 reduced/avoided, or null if not specified)
- methodology: string (verification standard or method used, e.g., "Verra VCS", "Gold Standard")
- summary: string (2–3 sentence summary of the project)

PROJECT REPORT:
\"\"\"
{report_text}
\"\"\"

Respond with ONLY the JSON object, no explanation.
"""

        raw = _call_llm(prompt)

        # Parse and return
        try:
            # Strip markdown code fences if present
            clean = raw.strip().strip("```json").strip("```").strip()
            result = json.loads(clean)
        except json.JSONDecodeError:
            result = {
                "project_name": "Unknown",
                "location": "Unknown",
                "timeline": "Unknown",
                "claimed_reduction_tco2": None,
                "methodology": "Unknown",
                "summary": raw,
            }

        return result
