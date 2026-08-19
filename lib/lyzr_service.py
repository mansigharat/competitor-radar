import os
import re
import json
import uuid
import logging
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("competitor_radar.lyzr")
logger.setLevel(logging.INFO)

# Default configuration from environment variables
LYZR_API_KEY = os.getenv("LYZR_API_KEY", "")
LYZR_USER_ID = os.getenv("LYZR_USER_ID", "user_competitor_radar")
LYZR_AGENT_ID = os.getenv("LYZR_AGENT_ID", "6a85ad59a8f70daca77f446d")
LYZR_API_URL = os.getenv("LYZR_API_URL", "https://agent-prod.studio.lyzr.ai/v3/inference/chat/")

class LyzrServiceError(Exception):
    """Custom exception for Lyzr API communication issues."""
    pass


def send_lyzr_message(
    message: str,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends a message to the deployed Lyzr Manager Agent securely server-side.
    Returns the raw response and parsed structured output.
    """
    api_key = os.getenv("LYZR_API_KEY", LYZR_API_KEY)
    user_id = os.getenv("LYZR_USER_ID", LYZR_USER_ID)
    target_agent_id = agent_id or os.getenv("LYZR_AGENT_ID", LYZR_AGENT_ID)
    api_url = os.getenv("LYZR_API_URL", LYZR_API_URL)

    if not api_key:
        logger.error("LYZR_API_KEY is missing from server environment.")
        raise LyzrServiceError("Server configuration error: LYZR_API_KEY is missing.")

    active_session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }

    payload = {
        "user_id": user_id,
        "agent_id": target_agent_id,
        "session_id": active_session_id,
        "message": message
    }

    logger.info(f"Sending message to Lyzr Agent {target_agent_id} (Session: {active_session_id})")

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        response_data = response.json()
        
        # Extract response message text from standard Lyzr envelope
        raw_text = ""
        if isinstance(response_data, dict):
            raw_text = (
                response_data.get("response") or 
                response_data.get("message") or 
                response_data.get("text") or 
                json.dumps(response_data)
            )
        else:
            raw_text = str(response_data)

        return {
            "success": True,
            "session_id": active_session_id,
            "raw_text": raw_text,
            "raw_response": response_data
        }

    except requests.exceptions.HTTPError as he:
        if he.response is not None and he.response.status_code == 403:
            error_msg = "Unable to complete the competitor scan. Invalid or missing LYZR_API_KEY in server environment. Please set your valid Lyzr API key in the server .env file."
        else:
            error_msg = f"Unable to complete the competitor analysis. API Error: {str(he)}"
        logger.error(error_msg)
        raise LyzrServiceError(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Unable to complete the competitor analysis. Network/API Error: {str(e)}"
        logger.error(error_msg)
        raise LyzrServiceError(error_msg)


def parse_competitor_discovery_response(raw_text: str) -> List[Dict[str, Any]]:
    """
    Resilient parser for Competitor Finder response.
    Extracts competitor list (NAME, WHY, CONFIDENCE, REGION, CATEGORY).
    Handles plain text (NAME:), bullet points (- **NAME:**), markdown headers, and direct line fallback.
    """
    competitors = []

    # Strategy 1: Parse direct JSON if present
    json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "name" in item:
                        competitors.append({
                            "name": str(item.get("name", "Unknown Competitor")).strip(),
                            "why": str(item.get("why", item.get("description", "Direct market overlap"))).strip(),
                            "confidence": str(item.get("confidence", "HIGH")).upper().strip(),
                            "region": str(item.get("region", "Global")).strip(),
                            "category": str(item.get("category", "Direct Competitor")).strip()
                        })
                if competitors:
                    return competitors
        except Exception:
            pass

    # Strategy 2: Split on NAME: (with or without markdown asterisks or bullet prefixes)
    name_blocks = re.split(r'(?=\s*(?:[\-\*\•]\s*)?\*?\*?NAME\*?\*?:\s*)', raw_text, flags=re.IGNORECASE)

    for block in name_blocks:
        block = block.strip()
        if not block:
            continue

        name_m = re.search(r'(?:[\-\*\•]\s*)?\*?\*?NAME\*?\*?:\s*([^\n]+)', block, re.IGNORECASE)
        if name_m:
            c_name = name_m.group(1).strip().strip('*').strip(':').strip()
            if c_name and len(c_name) < 60 and c_name.lower() not in ["name", "company", "why", "confidence", "region", "category"]:
                why_m = re.search(r'\*?\*?WHY\*?\*?:\s*([^\n]+)', block, re.IGNORECASE) or re.search(r'(?:WHY|Why|Description|Overlap):\s*([^\n]+)', block, re.IGNORECASE)
                conf_m = re.search(r'\*?\*?CONFIDENCE\*?\*?:\s*(HIGH|MEDIUM|LOW)', block, re.IGNORECASE) or re.search(r'(?:CONFIDENCE|Confidence):\s*(HIGH|MEDIUM|LOW)', block, re.IGNORECASE)
                reg_m = re.search(r'\*?\*?REGION\*?\*?:\s*([^\n]+)', block, re.IGNORECASE) or re.search(r'(?:REGION|Region):\s*([^\n]+)', block, re.IGNORECASE)
                cat_m = re.search(r'\*?\*?CATEGORY\*?\*?:\s*([^\n]+)', block, re.IGNORECASE) or re.search(r'(?:CATEGORY|Category):\s*([^\n]+)', block, re.IGNORECASE)

                why = why_m.group(1).strip().strip('*').strip() if why_m else "Active market competitor relevant to core business model."
                confidence = conf_m.group(1).upper().strip() if conf_m else "HIGH"
                region = reg_m.group(1).strip().strip('*').strip() if reg_m else "Regional"
                category = cat_m.group(1).strip().strip('*').strip() if cat_m else "Competitor"

                if not any(c["name"].lower() == c_name.lower() for c in competitors):
                    competitors.append({
                        "name": c_name,
                        "why": why,
                        "confidence": confidence,
                        "region": region,
                        "category": category
                    })

    if competitors:
        return competitors

    # Strategy 3: Direct Line Scan for all `NAME: <Name>` occurrences in text
    name_matches = re.finditer(r'(?:[\-\*\•]\s*)?\*?\*?NAME\*?\*?:\s*([^\n]+)', raw_text, re.IGNORECASE)
    for m in name_matches:
        c_name = m.group(1).strip().strip('*').strip(':').strip()
        if c_name and len(c_name) < 60 and c_name.lower() not in ["name", "company", "why", "confidence", "region", "category"]:
            if not any(c["name"].lower() == c_name.lower() for c in competitors):
                competitors.append({
                    "name": c_name,
                    "why": "Active market competitor relevant to core business model.",
                    "confidence": "HIGH",
                    "region": "Regional",
                    "category": "Competitor"
                })

    if competitors:
        return competitors

    # Strategy 4: Markdown Section / Numbered Block Parsing (e.g. ### Cashfree Payments or 1. Cashfree Payments)
    blocks = re.split(r'\n(?=(?:\#\#\#|\d+\.|\*?\*?Company\*?\*?:?|\*?\*?Competitor\*?\*?:?))', raw_text, flags=re.IGNORECASE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        name_match = (
            re.search(r'(?:^\#\#\#\s*|^\d+\.\s*|\*?\*?Name\*?\*?:\s*|\*?\*?Company\*?\*?:\s*|Competitor:\s*)([^\n\*]+)', block, re.IGNORECASE) or
            re.search(r'^\*\*(.*?)\*\*', block)
        )
        
        if name_match:
            name = name_match.group(1).strip().strip('*').strip(':').strip()
            if len(name) > 60 or name.lower() in ["why", "confidence", "region", "category", "competitors", "india", "southeast asia"]:
                continue

            why_match = re.search(r'(?:WHY|Why|Description|Overlap):\s*([^\n]+)', block, re.IGNORECASE)
            conf_match = re.search(r'(?:CONFIDENCE|Confidence):\s*(HIGH|MEDIUM|LOW)', block, re.IGNORECASE)
            reg_match = re.search(r'(?:REGION|Region):\s*([^\n]+)', block, re.IGNORECASE)
            cat_match = re.search(r'(?:CATEGORY|Category):\s*([^\n]+)', block, re.IGNORECASE)

            why = why_match.group(1).strip() if why_match else "Identified as active market competitor."
            confidence = conf_match.group(1).upper() if conf_match else "HIGH"
            region = reg_match.group(1).strip() if reg_match else "Regional"
            category = cat_match.group(1).strip() if cat_match else "Market Competitor"

            if not any(c["name"].lower() == name.lower() for c in competitors):
                competitors.append({
                    "name": name,
                    "why": why,
                    "confidence": confidence,
                    "region": region,
                    "category": category
                })

    return competitors


def parse_competitor_analysis_response(raw_text: str) -> Dict[str, Any]:
    """
    Resilient parser for Competitor Analyst and Response Options responses.
    Extracts:
    - CHANGE DETECTED: YES / NO
    - what_changed
    - why_it_matters
    - assessment
    - current_findings
    - response_options (only if change_detected == YES)
    """
    # Determine CHANGE DETECTED state
    change_detected = False
    
    # Check explicit keyword patterns
    if re.search(r'CHANGE\s*DETECTED\s*:\s*YES', raw_text, re.IGNORECASE) or re.search(r'MATERIAL\s*CHANGE\s*:\s*YES', raw_text, re.IGNORECASE):
        change_detected = True
    elif re.search(r'CHANGE\s*DETECTED\s*:\s*NO', raw_text, re.IGNORECASE) or re.search(r'NO\s*MATERIAL\s*CHANGE', raw_text, re.IGNORECASE):
        change_detected = False
    else:
        # Fallback heuristic: check if changes or strategic updates are described positive
        if "material change" in raw_text.lower() or "price change" in raw_text.lower() or "fee update" in raw_text.lower():
            change_detected = True

    # Extract Key Analysis Sections
    what_changed_match = re.search(r'(?:WHAT CHANGED|What Changed|Change Detected):\s*([^\n]+(?:\n(?!WHY IT MATTERS|ASSESSMENT|CURRENT FINDINGS|RESPONSE OPTIONS)[^\n]+)*)', raw_text, re.IGNORECASE)
    why_matters_match = re.search(r'(?:WHY IT MATTERS|Why It Matters|Strategic Impact):\s*([^\n]+(?:\n(?!ASSESSMENT|CURRENT FINDINGS|RESPONSE OPTIONS)[^\n]+)*)', raw_text, re.IGNORECASE)
    assessment_match = re.search(r'(?:ASSESSMENT|Assessment|Evaluation):\s*([^\n]+(?:\n(?!CURRENT FINDINGS|RESPONSE OPTIONS)[^\n]+)*)', raw_text, re.IGNORECASE)
    findings_match = re.search(r'(?:CURRENT FINDINGS|Current Findings|Observation):\s*([^\n]+(?:\n(?!RESPONSE OPTIONS)[^\n]+)*)', raw_text, re.IGNORECASE)

    what_changed = what_changed_match.group(1).strip() if what_changed_match else "Observation scan completed against recent competitor benchmarks."
    why_it_matters = why_matters_match.group(1).strip() if why_matters_match else "Impacts competitive positioning and customer acquisition dynamics."
    assessment = assessment_match.group(1).strip() if assessment_match else "Shift requires tactical oversight."
    current_findings = findings_match.group(1).strip() if findings_match else raw_text[:300]

    response_options = []

    # ONLY parse response options if change_detected is True
    if change_detected:
        # Look for response options blocks (e.g. Option 1, 01 HOLD & MONITOR, ### 1. Position Defense)
        option_blocks = re.split(r'\n(?=(?:Option\s*\d+|\d+\.\s*|\#\#\#\s*(?:Option|\d+)|OPTION\s*\d+))', raw_text, re.IGNORECASE)
        
        for ob in option_blocks:
            ob = ob.strip()
            if not ob:
                continue
                
            title_match = re.search(r'(?:Option\s*\d+:?|\d+\.\s*|\#\#\#\s*)([^\n]+)', ob, re.IGNORECASE)
            if title_match:
                opt_title = title_match.group(1).strip().strip('*').strip('#')
                if any(kw in opt_title.lower() for kw in ["what changed", "why it matters", "assessment", "findings", "change detected"]):
                    continue

                desc_match = re.search(r'(?:Description|Overview):\s*([^\n]+)', ob, re.IGNORECASE)
                reasoning_match = re.search(r'(?:Why It Makes Sense|Reasoning|Rationale):\s*([^\n]+)', ob, re.IGNORECASE)
                risk_match = re.search(r'(?:Risk|Consideration|Tradeoff):\s*([^\n]+)', ob, re.IGNORECASE)

                desc = desc_match.group(1).strip() if desc_match else ob[:150]
                reasoning = reasoning_match.group(1).strip() if reasoning_match else "Aligns with risk-calibrated strategy."
                risk = risk_match.group(1).strip() if risk_match else "Requires active execution monitoring."

                # Flag Hold & Monitor style options
                is_hold = "hold" in opt_title.lower() or "monitor" in opt_title.lower()

                response_options.append({
                    "title": opt_title,
                    "description": desc,
                    "why_it_makes_sense": reasoning,
                    "risk_consideration": risk,
                    "is_hold_and_monitor": is_hold
                })

    return {
        "change_detected": change_detected,
        "what_changed": what_changed,
        "why_it_matters": why_it_matters,
        "assessment": assessment,
        "current_findings": current_findings,
        "response_options": response_options,
        "raw_text": raw_text
    }
