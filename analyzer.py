"""LLM-powered claim extraction and analysis."""

import json
import anthropic
from config import ANTHROPIC_API_KEY, MODEL, RED_FLAG_PATTERNS

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

ANALYSIS_PROMPT = """You are a scientific skeptic and consumer protection analyst. Analyze this product page content and return a structured JSON evaluation.

## Page Content
Title: {title}
URL: {url}
Meta Description: {meta_description}

Body Text:
{body_text}

Disclaimers Found:
{disclaimers}

## Known Red Flag Patterns
{red_flag_patterns}

## Your Task

Analyze the page and return ONLY valid JSON with this exact structure:

{{
    "product_name": "Name of the primary product",
    "category": "Product category (e.g., Frequency device, EMF shield, Supplement, Detox, etc.)",
    "claims_extracted": [
        "Exact claim 1 quoted or closely paraphrased from the page",
        "Exact claim 2",
        ...
    ],
    "red_flags": [
        "Specific red flag found with brief explanation",
        ...
    ],
    "evidence_check": "Summary of whether any peer-reviewed evidence, clinical trials, or legitimate certifications are cited. Note what's missing.",
    "mechanism_plausibility": "Is there a plausible scientific mechanism for the product's claimed effects? Explain briefly.",
    "fda_disclaimer_present": true/false,
    "health_claims_despite_disclaimer": true/false,
    "unverifiable_statistics": [
        "Any percentage or number claims without methodology or source",
        ...
    ],
    "trust_score": 0-100,
    "trust_score_reasoning": "Brief explanation of score breakdown",
    "verdict": "One of: LEGIT | CAUTION | LIKELY SCAM | SCAM",
    "verdict_summary": "2-3 sentence plain-language summary a consumer would understand",
    "ftc_complaint_ready": true/false,
    "ftc_complaint_basis": "If complaint-ready, what specific violations could be cited"
}}

## Scoring Guidelines
- Start at 50 (neutral)
- Subtract 5-10 for each red flag pattern matched
- Subtract 10-15 for health claims with FDA disclaimer present (contradiction)
- Subtract 10 for unverifiable statistics
- Subtract 10 for no plausible mechanism of action
- Subtract 5 for each buzzword without scientific backing
- Add 10-15 for peer-reviewed citations
- Add 10 for transparent ingredient/component lists
- Add 5-10 for legitimate third-party certifications (not just FCC for electronics)
- Add 5 for clear, honest product descriptions without health overclaiming

Be rigorous but fair. Some wellness products have modest evidence — don't score them the same as outright fraud."""


def analyze_page(page_data: dict) -> dict:
    """Run LLM analysis on scraped page content. Returns structured evaluation."""
    prompt = ANALYSIS_PROMPT.format(
        title=page_data["title"],
        url=page_data["url"],
        meta_description=page_data["meta_description"],
        body_text=page_data["body_text"],
        disclaimers="\n".join(page_data["disclaimers"]) or "None found",
        red_flag_patterns="\n".join(f"- {p}" for p in RED_FLAG_PATTERNS),
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Extract JSON from response (handle markdown code blocks)
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    analysis = json.loads(raw_text)
    return analysis
