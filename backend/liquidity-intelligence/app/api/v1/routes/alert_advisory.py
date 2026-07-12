"""
POST /api/v1/alerts/{alert_id}/advisory
Generates an AI advisory for a specific alert, in the user's preferred language.
"""
from __future__ import annotations

import json
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from prisma import Prisma
from pydantic import BaseModel

from app.api.v1.deps import get_current_user, get_db
from app.core.config import get_settings
from app.domain.entities import User

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/alerts", tags=["Alert Advisory"])
settings = get_settings()


class AdvisoryResponse(BaseModel):
    alert_id: str
    language: str
    advisory: str
    recommendations: list[str]
    confidence_note: str
    severity_context: str


LANGUAGE_MAP = {
    "en": "English",
    "bn": "Bengali (বাংলা)",
    "banglish": "Banglish (Romanized Bengali)",
    "English": "English",
    "Bengali": "Bengali (বাংলা)",
    "Banglish": "Banglish (Romanized Bengali)",
    "Both": "Bengali (বাংলা)",
}


def _build_prompt(alert_data: dict, language: str, agent_name: str, snapshot_context: str) -> str:
    lang_label = LANGUAGE_MAP.get(language, "English")
    
    prompt = f"""You are an AI advisory system for MFS (Mobile Financial Services) super-agents in Bangladesh. 
You provide actionable, clear advisory messages to help agents manage their liquidity.

IMPORTANT: Respond ENTIRELY in {lang_label}. Every word of your response must be in {lang_label}.
{"Use বাংলা script for Bengali." if "Bengali" in lang_label else ""}
{"Use Romanized Bengali (English script for Bengali words)." if "Banglish" in lang_label else ""}

You are advising agent: {agent_name}

Alert Details:
- Type: {alert_data.get('alert_type', 'unknown')}
- Severity: {alert_data.get('severity', 'unknown')}
- Confidence: {alert_data.get('confidence', 0) * 100:.0f}%
- Evidence: {json.dumps(alert_data.get('evidence', {}), default=str)}
- Status: {alert_data.get('status', 'unknown')}
- Created: {alert_data.get('created_at', 'unknown')}

{snapshot_context}

Based on this alert, provide:
1. A clear explanation of what is happening (2-3 sentences max)
2. How certain the system is about this assessment
3. What the agent should do next (actionable recommendations)
4. Any important context (e.g., if this could be normal due to Eid, salary days, etc.)

RULES:
- This is ADVISORY ONLY. Never suggest executing financial transactions directly.
- Be specific about which provider is affected, the amounts, and timeframes.
- Express uncertainty honestly — say "may" or "likely" when confidence is below 85%.
- Keep recommendations safe and actionable.
- Be concise but informative.

Respond in this JSON format:
{{
  "advisory": "Main advisory message (2-3 sentences)",
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
  "confidence_note": "Brief note about how certain this assessment is",
  "severity_context": "One sentence explaining the severity level"
}}
"""
    return prompt


@router.post("/{alert_id}/advisory", response_model=AdvisoryResponse)
async def generate_alert_advisory(
    alert_id: str,
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """
    Get AI advisory for a specific alert. 
    Advisory is pre-generated at alert creation time by the Explainability + Recommendation agents.
    If no pre-generated advisory exists, generates one on-demand.
    """
    
    # Get alert
    alert_row = await db.alert.find_unique(where={"id": alert_id})
    if not alert_row:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Try to parse pre-stored advisory from notes field
    if alert_row.notes and alert_row.notes.strip().startswith("{"):
        try:
            stored = json.loads(alert_row.notes)
            if "advisory" in stored:
                # Get user language
                user_row = await db.user.find_unique(where={"id": user.id})
                user_language = user_row.language if user_row else "en"
                return AdvisoryResponse(
                    alert_id=alert_id,
                    language=user_language,
                    advisory=stored.get("advisory", ""),
                    recommendations=stored.get("recommendations", []),
                    confidence_note=stored.get("confidence_note", ""),
                    severity_context=stored.get("severity_context", ""),
                )
        except json.JSONDecodeError:
            pass

    # Fallback: generate on-demand if no pre-stored advisory
    # Get user's language preference
    user_row = await db.user.find_unique(where={"id": user.id})
    user_language = user_row.language if user_row else "en"

    # Get agent info
    agent_row = await db.agent.find_unique(where={"id": alert_row.agentId})
    agent_name = agent_row.name if agent_row else "Unknown Agent"

    # Get latest snapshot for context
    snapshot_context = ""
    latest_snapshot = await db.liquiditysnapshot.find_first(
        where={"agentId": alert_row.agentId},
        order={"capturedAt": "desc"},
    )
    if latest_snapshot:
        total = float(latest_snapshot.physicalCash + latest_snapshot.bkashBalance + latest_snapshot.nagadBalance + latest_snapshot.rocketBalance)
        snapshot_context = f"""
Current Liquidity Status:
- Physical Cash: ৳{float(latest_snapshot.physicalCash):,.0f}
- bKash Balance: ৳{float(latest_snapshot.bkashBalance):,.0f}
- Nagad Balance: ৳{float(latest_snapshot.nagadBalance):,.0f}
- Rocket Balance: ৳{float(latest_snapshot.rocketBalance):,.0f}
- Total Liquidity: ৳{total:,.0f}
- Confidence: {latest_snapshot.overallConfidence * 100:.0f}%
"""

    # Build alert data dict
    alert_data = {
        "alert_type": alert_row.alertType,
        "severity": alert_row.severity,
        "confidence": alert_row.confidence,
        "evidence": alert_row.evidence if isinstance(alert_row.evidence, dict) else {},
        "status": alert_row.status,
        "created_at": str(alert_row.createdAt),
    }

    # Call OpenAI
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=settings.openai_api_key)
        prompt = _build_prompt(alert_data, user_language, agent_name, snapshot_context)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an MFS liquidity advisory AI. Respond only with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=800,
        )

        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        parsed = json.loads(content)

        # Store the generated advisory in the alert's notes for future use
        advisory_json = json.dumps(parsed, ensure_ascii=False)
        await db.alert.update(
            where={"id": alert_id},
            data={"notes": advisory_json},
        )

        return AdvisoryResponse(
            alert_id=alert_id,
            language=user_language,
            advisory=parsed.get("advisory", "Advisory could not be generated."),
            recommendations=parsed.get("recommendations", []),
            confidence_note=parsed.get("confidence_note", ""),
            severity_context=parsed.get("severity_context", ""),
        )

    except json.JSONDecodeError:
        return AdvisoryResponse(
            alert_id=alert_id,
            language=user_language,
            advisory=content if content else "Advisory generation failed.",
            recommendations=["Please review this alert manually."],
            confidence_note="AI response could not be structured properly.",
            severity_context=f"Alert severity: {alert_data['severity']}",
        )
    except Exception as e:
        logger.error("advisory_generation_failed", error=str(e), alert_id=alert_id)
        return _fallback_advisory(alert_id, alert_data, user_language, snapshot_context)


def _fallback_advisory(alert_id: str, alert_data: dict, language: str, snapshot_context: str) -> AdvisoryResponse:
    """Generate a simple rule-based advisory when AI is unavailable."""
    
    alert_type = alert_data["alert_type"]
    severity = alert_data["severity"]
    evidence = alert_data.get("evidence", {})

    if language in ("bn", "Bengali", "Both"):
        # Bengali fallback
        if alert_type == "liquidity_low":
            provider = evidence.get("lowest_provider", "unknown")
            advisory = f"আপনার {provider} ব্যালেন্স কমে যাচ্ছে। মোট লিকুইডিটির তুলনায় এটি বিপদসীমার নিচে নেমে এসেছে।"
            recommendations = [
                f"{provider} ব্যালেন্স টপ-আপ করার বিষয়টি বিবেচনা করুন।",
                "পরবর্তী ২-৩ ঘণ্টা ক্যাশ-আউটের চাপ পর্যবেক্ষণ করুন।",
                "প্রয়োজনে টেরিটরি অফিসারের সাথে যোগাযোগ করুন।",
            ]
        elif alert_type == "liquidity_critical":
            provider = evidence.get("lowest_provider", "unknown")
            advisory = f"জরুরি: {provider} ব্যালেন্স প্রায় শেষ। গ্রাহকদের সেবা দেওয়া শীঘ্রই বন্ধ হয়ে যেতে পারে।"
            recommendations = [
                "অবিলম্বে রিফিল/টপ-আপের ব্যবস্থা করুন।",
                "টেরিটরি অফিসারকে জানান।",
                "বড় ক্যাশ-আউট অনুরোধ সাময়িকভাবে স্থগিত রাখুন।",
            ]
        elif alert_type == "anomaly_detected":
            flag_type = evidence.get("flag_type", "unknown")
            advisory = f"অস্বাভাবিক লেনদেনের ধরন শনাক্ত হয়েছে ({flag_type.replace('_', ' ')})। এটি মৌসুমী চাহিদার কারণেও হতে পারে।"
            recommendations = [
                "সাম্প্রতিক লেনদেনগুলো পর্যালোচনা করুন।",
                "ঈদ/বেতন দিবসের কারণে স্বাভাবিক হতে পারে কিনা বিবেচনা করুন।",
                "সন্দেহজনক মনে হলে বড় অঙ্কের লেনদেনের আগে যাচাই করুন।",
            ]
        else:
            advisory = f"একটি {severity} মাত্রার সতর্কতা সক্রিয় আছে। দয়া করে পর্যালোচনা করুন।"
            recommendations = ["সতর্কতাটি পর্যালোচনা করুন।", "প্রয়োজনে এস্কেলেট করুন।"]
        
        confidence_note = f"এই মূল্যায়নের নিশ্চয়তা: {alert_data['confidence'] * 100:.0f}%"
        severity_context = f"তীব্রতা: {severity} — " + ("অবিলম্বে পদক্ষেপ প্রয়োজন।" if severity in ("critical", "high") else "পর্যবেক্ষণ করুন।")
    
    else:
        # English fallback
        if alert_type == "liquidity_low":
            provider = evidence.get("lowest_provider", "unknown")
            advisory = f"Your {provider} balance is running low. It has dropped below the safe threshold relative to your total liquidity."
            recommendations = [
                f"Consider topping up your {provider} balance.",
                "Monitor cash-out pressure over the next 2-3 hours.",
                "Contact your territory officer if the situation worsens.",
            ]
        elif alert_type == "liquidity_critical":
            provider = evidence.get("lowest_provider", "unknown")
            advisory = f"URGENT: Your {provider} balance is nearly depleted. You may be unable to serve customers shortly."
            recommendations = [
                "Arrange an immediate refill/top-up.",
                "Notify your territory officer.",
                "Temporarily hold large cash-out requests until balance is restored.",
            ]
        elif alert_type == "anomaly_detected":
            flag_type = evidence.get("flag_type", "unknown")
            advisory = f"An unusual transaction pattern ({flag_type.replace('_', ' ')}) has been detected. This may be due to seasonal demand or legitimate activity."
            recommendations = [
                "Review recent transactions for this pattern.",
                "Consider if Eid/salary day could explain the surge.",
                "Verify identity for large transactions if pattern seems suspicious.",
            ]
        elif alert_type == "forecast_breach":
            provider = evidence.get("provider", "unknown")
            hours = evidence.get("predicted_depletion_hours", "unknown")
            advisory = f"Based on current trends, your {provider} balance is predicted to deplete within approximately {hours} hours."
            recommendations = [
                f"Plan to rebalance {provider} within the next few hours.",
                "Reduce large cash-out exposure on this provider if possible.",
                "Check if nearby agents can assist with float sharing.",
            ]
        else:
            advisory = f"A {severity}-severity alert is active. Please review."
            recommendations = ["Review the alert details.", "Escalate if needed."]
        
        confidence_note = f"System confidence in this assessment: {alert_data['confidence'] * 100:.0f}%"
        severity_context = f"Severity: {severity} — " + ("Immediate action recommended." if severity in ("critical", "high") else "Monitor the situation.")

    return AdvisoryResponse(
        alert_id=alert_id,
        language=language,
        advisory=advisory,
        recommendations=recommendations,
        confidence_note=confidence_note,
        severity_context=severity_context,
    )
