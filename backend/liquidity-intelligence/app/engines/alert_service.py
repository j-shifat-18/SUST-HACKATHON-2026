"""
AlertService — generates Alert entities from engine outputs, and uses
OpenAI Explainability + Recommendation agents to produce advisory messages
at alert creation time (so users never wait).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog

from app.core.config import get_settings
from app.engines.anomaly_engine import AnomalyResult

logger = structlog.get_logger(__name__)
settings = get_settings()

LANGUAGE_MAP = {
    "en": "English",
    "bn": "Bengali (বাংলা script only)",
    "banglish": "Banglish (Romanized Bengali using English letters)",
    "English": "English",
    "Bengali": "Bengali (বাংলা script only)",
    "Banglish": "Banglish (Romanized Bengali using English letters)",
    "Both": "Bengali (বাংলা script only)",
}


def _generate_ai_advisory(
    alert_type: str,
    severity: str,
    confidence: float,
    evidence: dict,
    language: str,
    agent_name: str,
    snapshot_info: Optional[dict] = None,
) -> dict:
    """
    Call OpenAI (Explainability + Recommendation agents) to generate
    an advisory message at alert creation time.
    Returns: {"advisory": str, "recommendations": [...], "confidence_note": str, "severity_context": str}
    """
    lang_label = LANGUAGE_MAP.get(language, "English")
    snapshot_str = ""
    if snapshot_info:
        snapshot_str = f"""
Current Liquidity:
- Physical: ৳{snapshot_info.get('physical_cash', 0):,.0f}
- bKash: ৳{snapshot_info.get('bkash', 0):,.0f}
- Nagad: ৳{snapshot_info.get('nagad', 0):,.0f}
- Rocket: ৳{snapshot_info.get('rocket', 0):,.0f}
- Total: ৳{snapshot_info.get('total', 0):,.0f}
"""

    prompt = f"""You are two AI agents working together for an MFS super-agent advisory system in Bangladesh:

**Explainability Agent**: Explain what is happening in clear, simple language. Be specific about providers, amounts, and timeframes. Never use the word "fraud" — use "unusual pattern" or "requires review".

**Recommendation Agent**: Provide 2-3 safe, actionable recommendations. Never suggest executing transactions. Only advisory.

RESPOND ENTIRELY IN {lang_label}. Every word must be in {lang_label}.
{"Use বাংলা script." if "Bengali" in lang_label and "Romanized" not in lang_label else ""}

Agent: {agent_name}
Alert Type: {alert_type.replace('_', ' ')}
Severity: {severity}
Confidence: {confidence * 100:.0f}%
Evidence: {json.dumps(evidence, default=str)}
{snapshot_str}

Produce a JSON response:
{{
  "advisory": "2-3 sentence explanation of what is happening and why (from Explainability Agent)",
  "recommendations": ["action 1", "action 2", "action 3"],
  "confidence_note": "How certain is this assessment (1 sentence)",
  "severity_context": "What the severity level means for the agent (1 sentence)"
}}"""

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an MFS liquidity advisory system. Respond only with valid JSON. No markdown fences."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        return json.loads(content)

    except Exception as e:
        logger.warning("ai_advisory_generation_failed", error=str(e))
        return _fallback_advisory(alert_type, severity, confidence, evidence, language)


def _fallback_advisory(
    alert_type: str,
    severity: str,
    confidence: float,
    evidence: dict,
    language: str,
) -> dict:
    """Rule-based fallback when OpenAI is unavailable."""
    
    if language in ("bn", "Bengali", "Both"):
        if alert_type == "liquidity_low":
            provider = evidence.get("lowest_provider", "একটি প্রোভাইডার")
            return {
                "advisory": f"আপনার {provider} ব্যালেন্স কমে যাচ্ছে। মোট লিকুইডিটির তুলনায় এটি নিরাপদ সীমার নিচে নেমে এসেছে। ক্যাশ-আউটের চাপ অব্যাহত থাকলে শীঘ্রই সেবা প্রদানে সমস্যা হতে পারে।",
                "recommendations": [
                    f"{provider} ব্যালেন্স রিফিল করার ব্যবস্থা নিন।",
                    "বড় অঙ্কের ক্যাশ-আউট অনুরোধে সতর্ক থাকুন।",
                    "প্রয়োজনে টেরিটরি অফিসারকে জানান।",
                ],
                "confidence_note": f"এই মূল্যায়নের নিশ্চয়তা {confidence * 100:.0f}%।",
                "severity_context": f"তীব্রতা: {severity} — " + ("অবিলম্বে পদক্ষেপ নিন।" if severity in ("critical", "high") else "পরিস্থিতি পর্যবেক্ষণ করুন।"),
            }
        elif alert_type == "liquidity_critical":
            provider = evidence.get("lowest_provider", "একটি প্রোভাইডার")
            return {
                "advisory": f"জরুরি: আপনার {provider} ই-মানি প্রায় শেষ হয়ে গেছে। বর্তমান ক্যাশ-আউটের ধারা অনুযায়ী অল্প সময়ের মধ্যে গ্রাহকদের সেবা দেওয়া সম্ভব হবে না।",
                "recommendations": [
                    "এখনই রিফিল/টপ-আপের ব্যবস্থা করুন।",
                    "টেরিটরি অফিসারকে অবিলম্বে জানান।",
                    "বড় ক্যাশ-আউট সাময়িকভাবে স্থগিত রাখুন।",
                ],
                "confidence_note": f"নিশ্চয়তা {confidence * 100:.0f}% — অবিলম্বে পদক্ষেপ প্রয়োজন।",
                "severity_context": "জরুরি অবস্থা — নিরবচ্ছিন্ন সেবা নিশ্চিত করতে এখনই পদক্ষেপ নিন।",
            }
        elif alert_type == "anomaly_detected":
            flag_type = evidence.get("flag_type", "অজানা")
            if flag_type == "velocity_spike":
                count = evidence.get("hourly_count", "অনেক")
                normal = evidence.get("normal_hourly_count", "কম")
                return {
                    "advisory": f"গত এক ঘণ্টায় অস্বাভাবিক পরিমাণে লেনদেন হয়েছে ({count}টি, স্বাভাবিক {normal}টি)। সবচেয়ে বেশি চাপ আসছে বিকাশ ক্যাশ-আউটে। নিরাপদভাবে সেবা চালু রাখতে কমপক্ষে ২০,০০০ টাকা অতিরিক্ত নগদ ব্যবস্থা করার পরামর্শ দেওয়া হচ্ছে।",
                    "recommendations": [
                        "সাম্প্রতিক লেনদেনগুলো পর্যালোচনা করুন।",
                        "ঈদ/বেতন দিবসের কারণে স্বাভাবিক হতে পারে কিনা বিবেচনা করুন।",
                        "সন্দেহজনক মনে হলে বড় লেনদেনে গ্রাহক যাচাই করুন।",
                    ],
                    "confidence_note": f"মূল্যায়নের নিশ্চয়তা {confidence * 100:.0f}%। ঈদ-পূর্ব স্বাভাবিক চাহিদাও হতে পারে।",
                    "severity_context": "অস্বাভাবিক প্যাটার্ন — সরবরাহের আগে লেনদেনগুলো পর্যালোচনা করা প্রয়োজন।",
                }
            elif flag_type == "transaction_splitting":
                account = evidence.get("account_ref", "অজানা")
                count = evidence.get("transaction_count", 3)
                return {
                    "advisory": f"গত ১২ মিনিটে স্বাভাবিকের তুলনায় অনেক বেশি ক্যাশ-আউট হয়েছে। কয়েকটি লেনদেনের পরিমাণ প্রায় একই এবং অ্যাকাউন্ট ({account}) থেকে বারবার অনুরোধ এসেছে। এটি ঈদ-পূর্ব স্বাভাবিক চাহিদাও হতে পারে, তবে বড় অঙ্কের নগদ পুনরায় সরবরাহের আগে লেনদেনগুলো পর্যালোচনা করা প্রয়োজন।",
                    "recommendations": [
                        "একই অ্যাকাউন্ট থেকে পুনরাবৃত্তি লেনদেন যাচাই করুন।",
                        "বড় অঙ্কের লেনদেনে গ্রাহকের পরিচয় নিশ্চিত করুন।",
                        "সন্দেহজনক মনে হলে এস্কেলেট করুন।",
                    ],
                    "confidence_note": f"নিশ্চয়তা {confidence * 100:.0f}% — স্বাভাবিক কারণও থাকতে পারে।",
                    "severity_context": "পর্যালোচনা প্রয়োজন — তবে এখনই বড় পদক্ষেপ নেওয়ার দরকার নেই।",
                }
            else:
                return {
                    "advisory": "একটি অস্বাভাবিক লেনদেনের ধরন শনাক্ত হয়েছে। দয়া করে সাম্প্রতিক লেনদেন পর্যালোচনা করুন।",
                    "recommendations": ["লেনদেন পর্যালোচনা করুন।", "প্রয়োজনে এস্কেলেট করুন।"],
                    "confidence_note": f"নিশ্চয়তা: {confidence * 100:.0f}%",
                    "severity_context": f"তীব্রতা: {severity}",
                }
        elif alert_type == "forecast_breach":
            provider = evidence.get("provider", "একটি প্রোভাইডার")
            hours = evidence.get("predicted_depletion_hours", "কিছু")
            return {
                "advisory": f"বর্তমান লেনদেনের ধারা অনুযায়ী আগামী {hours} ঘণ্টার মধ্যে আপনার {provider} ই-মানি শেষ হয়ে যেতে পারে। সবচেয়ে বেশি চাপ আসছে ক্যাশ-আউটে।",
                "recommendations": [
                    f"{provider} ব্যালেন্স রিফিল পরিকল্পনা করুন।",
                    "বড় ক্যাশ-আউটে সতর্ক থাকুন।",
                    "নিকটস্থ এজেন্টের সাথে ফ্লোট শেয়ারিং বিবেচনা করুন।",
                ],
                "confidence_note": f"পূর্বাভাসের নিশ্চয়তা: {confidence * 100:.0f}%",
                "severity_context": f"তীব্রতা: {severity} — সময়মতো ব্যবস্থা নিন।",
            }
        else:
            return {
                "advisory": "একটি সতর্কতা সক্রিয় আছে।",
                "recommendations": ["পর্যালোচনা করুন।"],
                "confidence_note": f"নিশ্চয়তা: {confidence * 100:.0f}%",
                "severity_context": f"তীব্রতা: {severity}",
            }
    else:
        # English fallback
        if alert_type == "liquidity_low":
            provider = evidence.get("lowest_provider", "a provider")
            return {
                "advisory": f"Your {provider} balance is running low relative to total liquidity. If cash-out pressure continues, you may be unable to serve customers soon.",
                "recommendations": [
                    f"Top up your {provider} balance.",
                    "Monitor cash-out pressure for the next 2-3 hours.",
                    "Contact territory officer if situation worsens.",
                ],
                "confidence_note": f"Assessment confidence: {confidence * 100:.0f}%.",
                "severity_context": f"Severity: {severity} — " + ("take immediate action." if severity in ("critical", "high") else "monitor closely."),
            }
        elif alert_type == "anomaly_detected":
            flag_type = evidence.get("flag_type", "unknown")
            return {
                "advisory": f"An unusual transaction pattern ({flag_type.replace('_', ' ')}) has been detected. This requires review but may also be caused by seasonal demand.",
                "recommendations": [
                    "Review recent transactions.",
                    "Consider if this could be Eid/salary day demand.",
                    "Verify customer identity for large transactions if suspicious.",
                ],
                "confidence_note": f"Confidence: {confidence * 100:.0f}%. May be legitimate activity.",
                "severity_context": f"Severity: {severity} — review recommended before major action.",
            }
        else:
            return {
                "advisory": f"A {severity}-level {alert_type.replace('_', ' ')} alert is active.",
                "recommendations": ["Review the situation.", "Escalate if needed."],
                "confidence_note": f"Confidence: {confidence * 100:.0f}%",
                "severity_context": f"Severity: {severity}",
            }


def create_alert_from_anomaly(
    anomaly: AnomalyResult,
    agent_id: str,
    agent_name: str,
    user_language: str,
    snapshot_info: Optional[dict] = None,
) -> dict:
    """
    Create alert data dict with pre-generated AI advisory message.
    Returns a dict ready for DB insertion.
    """
    # Determine severity
    if anomaly.severity_score >= 70:
        severity = "high"
    elif anomaly.severity_score >= 50:
        severity = "medium"
    else:
        severity = "low"

    evidence = {
        "flag_type": anomaly.flag_type,
        "severity_score": anomaly.severity_score,
        **anomaly.evidence,
    }

    # Generate AI advisory at creation time
    advisory = _generate_ai_advisory(
        alert_type="anomaly_detected",
        severity=severity,
        confidence=anomaly.confidence,
        evidence=evidence,
        language=user_language,
        agent_name=agent_name,
        snapshot_info=snapshot_info,
    )

    alert_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    return {
        "id": alert_id,
        "agent_id": agent_id,
        "alert_type": "anomaly_detected",
        "severity": severity,
        "confidence": anomaly.confidence,
        "evidence": evidence,
        "status": "open",
        "notes": json.dumps(advisory, ensure_ascii=False),
        "created_at": now,
        "updated_at": now,
        "transaction_ids": anomaly.transaction_ids,
    }


def create_liquidity_alert(
    agent_id: str,
    agent_name: str,
    user_language: str,
    is_critical: bool,
    lowest_provider: str,
    lowest_balance: float,
    total_liquidity: float,
    snapshot_info: Optional[dict] = None,
) -> dict:
    """Create a liquidity alert with pre-generated advisory."""
    alert_type = "liquidity_critical" if is_critical else "liquidity_low"
    severity = "critical" if is_critical else "high"
    confidence = 0.92 if is_critical else 0.85

    evidence = {
        "lowest_provider": lowest_provider,
        f"{lowest_provider}_bdt": lowest_balance,
        "total_liquidity_bdt": total_liquidity,
        "pct_of_total": round(lowest_balance / total_liquidity * 100, 1) if total_liquidity > 0 else 0,
    }

    advisory = _generate_ai_advisory(
        alert_type=alert_type,
        severity=severity,
        confidence=confidence,
        evidence=evidence,
        language=user_language,
        agent_name=agent_name,
        snapshot_info=snapshot_info,
    )

    alert_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    return {
        "id": alert_id,
        "agent_id": agent_id,
        "alert_type": alert_type,
        "severity": severity,
        "confidence": confidence,
        "evidence": evidence,
        "status": "open",
        "notes": json.dumps(advisory, ensure_ascii=False),
        "created_at": now,
        "updated_at": now,
    }
