"""Earnings Call NLP & Tone Analyzer Agent — FinBERT-powered transcript analysis.

P1 Academic Edge Agent. Analyzes earnings call transcripts to extract
sentiment signals, with emphasis on CFO tone (more predictive than CEO tone).

Academic basis: FinBERT achieves F1 > 70% on StockTwits. CFO tone during Q&A
outpredicts CEO prepared remarks. Tone deterioration quarter-over-quarter is
more predictive than absolute tone level.

Sub-agents:
- Transcript Ingestion: Monitors Benzinga for new earnings call transcripts
- FinBERT Tone Scoring: Per-paragraph sentiment, CEO vs CFO scoring
- Keyword Extraction: Hedging, guidance, and risk language frequency
- Surprise Detection: EPS/revenue surprise vs tone divergence analysis

Council integration: hypothesis_agent reads earnings.tone_score,
earnings.cfo_delta, and earnings.surprise_tone_divergence.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "earnings_tone_agent"

# Hedging language indicators
_HEDGING_WORDS = {
    "might", "could", "possibly", "uncertain", "unclear", "depending",
    "if", "whether", "potentially", "may", "perhaps", "roughly",
}

# Forward guidance language
_GUIDANCE_WORDS = {
    "expect", "anticipate", "target", "forecast", "project", "guide",
    "outlook", "trajectory", "confident", "committed", "on track",
}

# Risk / concern language
_RISK_WORDS = {
    "headwinds", "challenging", "softness", "pressure", "weakness",
    "deterioration", "decline", "difficult", "concern", "cautious",
    "downturn", "recession", "contraction", "uncertainty",
}


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze most recent earnings call transcript for the symbol."""
    cfg = get_agent_thresholds()
    f = features.get("features", features)
    blackboard = context.get("blackboard")

    # Fetch latest earnings transcript
    transcript = await _fetch_transcript(symbol)
    if not transcript:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No earnings transcript available",
            weight=cfg.get("weight_earnings_tone_agent", 0.8),
            metadata={"data_available": False},
        )

    # Split into prepared remarks vs Q&A, identify speakers
    sections = _split_transcript(transcript)

    # Run tone analysis (FinBERT via brain_service or fallback)
    tone_results = await _analyze_tone(sections)

    # Keyword extraction
    keywords = _extract_keywords(transcript.get("text", ""))

    # Surprise detection
    surprise_data = _detect_surprise(f, tone_results)

    # Compute composite scores
    ceo_tone = tone_results.get("ceo_tone", 0.0)
    cfo_tone = tone_results.get("cfo_tone", 0.0)
    overall_tone = tone_results.get("overall_tone", 0.0)
    cfo_delta = tone_results.get("cfo_delta", 0.0)
    surprise_divergence = surprise_data.get("divergence", 0.0)

    # Write to blackboard
    if blackboard:
        blackboard.earnings.update({
            "tone_score": overall_tone,
            "cfo_delta": cfo_delta,
            "ceo_tone": ceo_tone,
            "cfo_tone": cfo_tone,
            "surprise_tone_divergence": surprise_divergence,
            "hedging_ratio": keywords.get("hedging_ratio", 0.0),
            "last_transcript_ticker": symbol,
        })

    # Vote determination
    direction, confidence = _tone_to_vote(
        overall_tone, cfo_tone, cfo_delta, surprise_divergence, keywords, cfg,
    )

    reasoning = (
        f"Earnings tone: overall={overall_tone:+.2f}, "
        f"CEO={ceo_tone:+.2f}, CFO={cfo_tone:+.2f}, "
        f"CFO Δ={cfo_delta:+.2f}, "
        f"surprise_div={surprise_divergence:+.2f}, "
        f"hedging={keywords.get('hedging_ratio', 0):.1%}"
    )

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=cfg.get("weight_earnings_tone_agent", 0.8),
        metadata={
            "data_available": True,
            "ceo_tone": ceo_tone,
            "cfo_tone": cfo_tone,
            "cfo_delta": cfo_delta,
            "overall_tone": overall_tone,
            "surprise_divergence": surprise_divergence,
            "keywords": keywords,
        },
    )


def _tone_to_vote(
    overall: float, cfo: float, cfo_delta: float,
    surprise_div: float, keywords: Dict, cfg: Dict,
) -> Tuple[str, float]:
    """Convert tone analysis to directional vote."""
    score = 0.0

    # CFO tone is weighted more heavily than CEO (academic finding)
    score += cfo * 0.35
    score += overall * 0.2

    # Tone deterioration is more predictive than absolute level
    if cfo_delta < -0.2:
        score -= 0.15  # CFO getting more negative
    elif cfo_delta > 0.2:
        score += 0.1   # CFO getting more positive

    # Surprise-tone divergence: beat with cautious tone = bearish
    if surprise_div > 0.3:
        score -= 0.1  # Earnings beat but tone dropped
    elif surprise_div < -0.3:
        score += 0.1  # Miss but confident tone = potential turnaround

    # Hedging language penalty
    hedging = keywords.get("hedging_ratio", 0)
    if hedging > 0.05:
        score -= hedging * 2

    # Risk language penalty
    risk_ratio = keywords.get("risk_ratio", 0)
    if risk_ratio > 0.03:
        score -= risk_ratio * 3

    # Map score to vote
    if score > 0.15:
        return "buy", min(0.85, 0.5 + abs(score))
    elif score < -0.15:
        return "sell", min(0.85, 0.5 + abs(score))
    else:
        return "hold", 0.4


async def _fetch_transcript(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch the most recent earnings call transcript."""
    # Try Benzinga
    try:
        from app.services.benzinga_service import get_earnings_transcript
        return await get_earnings_transcript(symbol)
    except Exception:
        pass

    # Try cached transcripts
    try:
        from app.services.transcript_cache import get_latest_transcript
        return await get_latest_transcript(symbol)
    except Exception:
        pass

    return None


def _split_transcript(transcript: Dict) -> Dict[str, Any]:
    """Split transcript into prepared remarks vs Q&A, identify speakers."""
    text = transcript.get("text", "")
    sections: Dict[str, Any] = {
        "prepared_remarks": "",
        "qa_section": "",
        "ceo_paragraphs": [],
        "cfo_paragraphs": [],
        "analyst_questions": [],
    }

    # Split on common Q&A markers
    qa_markers = ["question-and-answer", "q&a session", "q & a", "questions and answers"]
    qa_start = len(text)
    text_lower = text.lower()
    for marker in qa_markers:
        idx = text_lower.find(marker)
        if 0 < idx < qa_start:
            qa_start = idx

    sections["prepared_remarks"] = text[:qa_start]
    sections["qa_section"] = text[qa_start:]

    # Identify CEO/CFO paragraphs by speaker labels
    paragraphs = text.split("\n")
    current_speaker = ""
    for para in paragraphs:
        para_lower = para.lower().strip()
        if any(title in para_lower for title in ["ceo", "chief executive"]):
            current_speaker = "ceo"
        elif any(title in para_lower for title in ["cfo", "chief financial"]):
            current_speaker = "cfo"
        elif para_lower.startswith("analyst") or para_lower.startswith("q:"):
            current_speaker = "analyst"

        if current_speaker == "ceo" and len(para.strip()) > 20:
            sections["ceo_paragraphs"].append(para.strip())
        elif current_speaker == "cfo" and len(para.strip()) > 20:
            sections["cfo_paragraphs"].append(para.strip())

    return sections


async def _analyze_tone(sections: Dict) -> Dict[str, float]:
    """Run FinBERT tone scoring via brain_service or keyword fallback."""
    results = {
        "overall_tone": 0.0,
        "ceo_tone": 0.0,
        "cfo_tone": 0.0,
        "cfo_delta": 0.0,
        "qa_tone": 0.0,
    }

    # Try brain_service (FinBERT on RTX GPU)
    try:
        from app.services.brain_client import get_brain_client
        brain = get_brain_client()

        all_text = sections.get("prepared_remarks", "") + " " + sections.get("qa_section", "")
        if all_text.strip():
            overall = await brain.analyze_sentiment(all_text[:4000], model="finbert")
            results["overall_tone"] = overall.get("score", 0.0)

        ceo_text = " ".join(sections.get("ceo_paragraphs", []))
        if ceo_text:
            ceo_result = await brain.analyze_sentiment(ceo_text[:2000], model="finbert")
            results["ceo_tone"] = ceo_result.get("score", 0.0)

        cfo_text = " ".join(sections.get("cfo_paragraphs", []))
        if cfo_text:
            cfo_result = await brain.analyze_sentiment(cfo_text[:2000], model="finbert")
            results["cfo_tone"] = cfo_result.get("score", 0.0)

        qa_text = sections.get("qa_section", "")
        if qa_text:
            qa_result = await brain.analyze_sentiment(qa_text[:3000], model="finbert")
            results["qa_tone"] = qa_result.get("score", 0.0)

        return results
    except Exception:
        pass

    # Fallback: keyword-based tone analysis
    all_text = sections.get("prepared_remarks", "") + " " + sections.get("qa_section", "")
    results["overall_tone"] = _keyword_sentiment(all_text)

    ceo_text = " ".join(sections.get("ceo_paragraphs", []))
    results["ceo_tone"] = _keyword_sentiment(ceo_text) if ceo_text else 0.0

    cfo_text = " ".join(sections.get("cfo_paragraphs", []))
    results["cfo_tone"] = _keyword_sentiment(cfo_text) if cfo_text else 0.0

    qa_text = sections.get("qa_section", "")
    results["qa_tone"] = _keyword_sentiment(qa_text) if qa_text else 0.0

    return results


def _keyword_sentiment(text: str) -> float:
    """Simple keyword-based sentiment as fallback when FinBERT unavailable."""
    if not text:
        return 0.0
    words = text.lower().split()
    total = len(words)
    if total == 0:
        return 0.0

    positive = {"strong", "growth", "improving", "confident", "exceeded", "record",
                "beat", "outperformed", "momentum", "accelerating", "robust"}
    negative = {"weak", "decline", "deteriorating", "miss", "below", "challenging",
                "difficult", "concern", "pressure", "contraction", "headwinds"}

    pos_count = sum(1 for w in words if w in positive)
    neg_count = sum(1 for w in words if w in negative)

    return (pos_count - neg_count) / max(1, pos_count + neg_count)


def _extract_keywords(text: str) -> Dict[str, float]:
    """Extract hedging, guidance, and risk language frequencies."""
    if not text:
        return {"hedging_ratio": 0, "guidance_ratio": 0, "risk_ratio": 0}

    words = text.lower().split()
    total = max(1, len(words))

    hedging = sum(1 for w in words if w in _HEDGING_WORDS)
    guidance = sum(1 for w in words if w in _GUIDANCE_WORDS)
    risk = sum(1 for w in words if w in _RISK_WORDS)

    return {
        "hedging_ratio": round(hedging / total, 4),
        "guidance_ratio": round(guidance / total, 4),
        "risk_ratio": round(risk / total, 4),
        "hedging_count": hedging,
        "guidance_count": guidance,
        "risk_count": risk,
    }


def _detect_surprise(features: Dict, tone: Dict) -> Dict[str, Any]:
    """Detect earnings surprise vs tone divergence.

    A beat with cautious tone = bearish (guidance about to drop).
    A miss with confident tone = potentially bullish (turnaround).
    """
    eps_surprise = float(features.get("eps_surprise", 0) or features.get("earnings_surprise", 0))
    revenue_surprise = float(features.get("revenue_surprise", 0))

    # Normalize surprise to -1 to +1 range
    surprise_score = 0.0
    if eps_surprise > 0:
        surprise_score = min(1.0, eps_surprise / 0.5)  # Normalize by typical surprise
    elif eps_surprise < 0:
        surprise_score = max(-1.0, eps_surprise / 0.5)

    overall_tone = tone.get("overall_tone", 0.0)

    # Divergence: positive surprise + negative tone = bearish divergence
    divergence = surprise_score - overall_tone

    return {
        "eps_surprise": eps_surprise,
        "revenue_surprise": revenue_surprise,
        "surprise_score": surprise_score,
        "divergence": round(divergence, 3),
    }
