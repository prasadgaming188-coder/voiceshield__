def contextual_adjustment(context):
    score = 0.0
    reasons = []

    if not context.get("known_contact", True):
        score += 10
        reasons.append("Caller is not in the known-contact list.")
    if context.get("call_origin", "Known") == "Unknown":
        score += 8
        reasons.append("Call origin is unknown.")
    if float(context.get("transaction_amount", 0) or 0) >= 100000:
        score += 12
        reasons.append("High-value transaction context.")
    if context.get("previous_fraud_flag", False):
        score += 15
        reasons.append("Historical fraud indicator is present.")
    if context.get("sensitive_action", True):
        score += 5
        reasons.append("Sensitive action is requested.")

    return min(score, 40.0), reasons

def combine_risk(voice_risk, context):
    adjustment, reasons = contextual_adjustment(context)
    final = min(100.0, round(float(voice_risk) + adjustment, 1))

    if final >= 70:
        level = "HIGH"
        recommendation = (
            "PAUSE the sensitive action. Verify through a trusted callback, "
            "MFA and supervisor escalation before proceeding."
        )
    elif final >= 40:
        level = "MEDIUM"
        recommendation = (
            "Use secondary verification such as callback or MFA before "
            "approving the requested sensitive action."
        )
    else:
        level = "LOW"
        recommendation = (
            "No immediate voice-integrity alert. Continue normal verification controls."
        )
    return final, level, recommendation, adjustment, reasons
