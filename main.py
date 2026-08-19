import os
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from lib.lyzr_service import (
    send_lyzr_message,
    parse_competitor_discovery_response,
    parse_competitor_analysis_response,
    LyzrServiceError
)

# Load environment
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("competitor_radar")

app = FastAPI(
    title="Competitive Intelligence & Strategic Response System",
    description="Backend API proxy and static host for Competitor Radar powered by Lyzr Manager Agent",
    version="1.0.0"
)

# Static files mounting
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Request Models
class CompetitorRadarRequest(BaseModel):
    action: str = Field(..., description="Action type: 'discover' or 'analyze'")
    session_id: Optional[str] = Field(None, description="Lyzr session tracking ID")
    
    # Discovery Fields
    company_name: Optional[str] = Field("PayFlow", description="Company Name")
    what_we_do: Optional[str] = Field(None, description="What We Do")
    target_customers: Optional[str] = Field(None, description="Target Customers")
    region: Optional[str] = Field(None, description="Region")
    differentiator: Optional[str] = Field(None, description="Differentiator")
    
    # Analysis Fields
    competitor_name: Optional[str] = Field(None, description="Selected competitor to track")
    previous_payout_fee: Optional[str] = Field(None, description="Previous Payout Fee observation")
    previous_settlement: Optional[str] = Field(None, description="Previous Settlement observation")
    previous_service: Optional[str] = Field(None, description="Previous Service / Product observation")
    other_observation: Optional[str] = Field(None, description="Other observations")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the single-page application index.html"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Competitor Radar UI loading...</h1>", status_code=200)


@app.post("/api/competitor-radar")
async def handle_competitor_radar(req: CompetitorRadarRequest):
    """
    Secure Server-side API route proxying requests to deployed Lyzr Manager Agent.
    NEVER exposes Lyzr API key to the client browser.
    """
    logger.info(f"Received request action: {req.action}")

    try:
        if req.action == "discover":
            # Construct discovery prompt for Lyzr Manager Agent / Competitor Finder
            prompt = (
                f"Perform competitor discovery for company: '{req.company_name}'.\n"
                f"- What We Do: {req.what_we_do or 'Payment infrastructure'}\n"
                f"- Target Customers: {req.target_customers or 'Businesses and consumers'}\n"
                f"- Region: {req.region or 'India & Southeast Asia'}\n"
                f"- Differentiator: {req.differentiator or 'Direct bank integration'}\n\n"
                "Task: Identify relevant competitors operating in this space. "
                "For each competitor, provide:\n"
                "NAME: <Competitor Name>\n"
                "WHY: <One-sentence competitive overlap>\n"
                "CONFIDENCE: HIGH | MEDIUM | LOW\n"
                "REGION: <Geographic operating region>\n"
                "CATEGORY: <Category tag, e.g. Payment Rail, Infrastructure, Consumer>\n"
            )

            lyzr_res = send_lyzr_message(
                message=prompt,
                session_id=req.session_id
            )

            raw_text = lyzr_res.get("raw_text", "")
            competitors = parse_competitor_discovery_response(raw_text)

            return JSONResponse(content={
                "success": True,
                "action": "discover",
                "session_id": lyzr_res.get("session_id"),
                "competitors": competitors,
                "raw_text": raw_text
            })

        elif req.action == "analyze":
            if not req.competitor_name:
                raise HTTPException(status_code=400, detail="competitor_name is required for analysis.")

            # Construct analysis prompt for Lyzr Manager Agent / Competitor Analyst & Response Options
            prompt = (
                f"Analyze competitive change for target competitor: '{req.competitor_name}'.\n"
                f"My Company: '{req.company_name}' ({req.what_we_do}).\n\n"
                f"Previous Observation Benchmark for {req.competitor_name}:\n"
                f"- Payout Fee: {req.previous_payout_fee or 'Not specified'}\n"
                f"- Settlement Speed: {req.previous_settlement or 'Not specified'}\n"
                f"- Service / Product: {req.previous_service or 'Not specified'}\n"
                f"- Additional Notes: {req.other_observation or 'None'}\n\n"
                "Task:\n"
                "1. Compare current market observation for this competitor against the previous observation.\n"
                "2. Clearly state 'CHANGE DETECTED: YES' or 'CHANGE DETECTED: NO'.\n"
                "3. If CHANGE DETECTED: YES, output:\n"
                "   - WHAT CHANGED: <Detailed change>\n"
                "   - WHY IT MATTERS: <Strategic implications>\n"
                "   - ASSESSMENT: <Evaluation>\n"
                "   - CURRENT FINDINGS: <Current facts>\n"
                "   - 3 Practical Strategic RESPONSE OPTIONS for my company (Option title, Description, Why it makes sense, Risk/consideration, including Hold & Monitor).\n"
                "4. If CHANGE DETECTED: NO, output 'NO MATERIAL CHANGE' and state that no response options are needed."
            )

            lyzr_res = send_lyzr_message(
                message=prompt,
                session_id=req.session_id
            )

            raw_text = lyzr_res.get("raw_text", "")
            analysis_result = parse_competitor_analysis_response(raw_text)

            return JSONResponse(content={
                "success": True,
                "action": "analyze",
                "competitor_name": req.competitor_name,
                "session_id": lyzr_res.get("session_id"),
                "analysis": analysis_result,
                "raw_text": raw_text
            })

        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {req.action}")

    except LyzrServiceError as lse:
        logger.error(f"Lyzr service error: {str(lse)}")
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "error": "Unable to complete the competitor analysis.",
                "detail": str(lse)
            }
        )
    except Exception as e:
        logger.error(f"Unhandled error in API route: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Unable to complete the competitor analysis.",
                "detail": str(e)
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
