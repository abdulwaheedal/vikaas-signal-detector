from datetime import datetime, timezone
from utils.parser import detect_author_role, score_ownership_language, build_full_text
from signals.detector import detect_themes, score_themes, score_specificity, get_all_matched_keywords


def compute_signal(entry):
    """
    Takes a raw entry dict and returns a scored signal record,
    or None if the entry has no detected pain themes.

    Final score = sum of four dimensions, each 0-25, total 0-100:

    1. Role score      — Who is speaking? CHRO=25, analyst=3, unknown=0
    2. Ownership score — Are they in the pain or observing it?
                         "our process" = high, "companies struggle" = low
    3. Theme score     — Is a real pain theme present? How many?
    4. Specificity score — Numbers, timeframes, named outcomes?

    A score of 80+ = strong signal: senior person, owns the problem,
                     specific about the pain.
    A score of 40-60 = weak signal: real topic but vague or wrong author type.
    A score below 40 = noise: analyst reporting, no ownership, generic.
    """

    full_text = build_full_text(entry)

    # --- Dimension 1: Role ---
    role_result = detect_author_role(entry.get("author", ""), full_text)
    role_score = role_result["score"]

    # --- Dimension 2: Ownership language ---
    ownership_result = score_ownership_language(full_text)
    ownership_score = ownership_result["score"]

    # --- Dimension 3: Theme ---
    detected_themes = detect_themes(full_text)
    if not detected_themes:
        # No pain theme found — not a signal, skip entirely
        return None
    theme_score = score_themes(detected_themes)

    # --- Dimension 4: Specificity ---
    specificity_score = score_specificity(full_text)

    # --- Final score ---
    total_score = role_score + ownership_score + theme_score + specificity_score

    # --- Build the output record ---
    matched_keywords = get_all_matched_keywords(detected_themes)
    theme_names = [t["theme_name"] for t in detected_themes]
    primary_theme = detected_themes[0]["theme_name"]

    record = {
        "company": extract_company(entry.get("author", "")),
        "signal_type": primary_theme,
        "source_url": entry.get("url", ""),
        "matched_keywords": matched_keywords,
        "signal_score": total_score,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "reason": build_reason(
            role_result, ownership_result, theme_names,
            specificity_score, total_score
        ),
        "_debug": {
            "author": entry.get("author", ""),
            "source": entry.get("source_name", ""),
            "role_score": role_score,
            "ownership_score": ownership_score,
            "theme_score": theme_score,
            "specificity_score": specificity_score,
            "all_themes": theme_names,
        }
    }

    return record


def extract_company(author_string):
    """
    Attempts to extract company name from author byline.
    e.g. "Sarah Chen, CHRO at Meridian Health" -> "Meridian Health"
    Falls back to "Unknown" if pattern doesn't match.
    """
    # Match "at <Company>" or "@ <Company>"
    import re
    match = re.search(r'\b(?:at|@)\s+([A-Z][^\,\.]+)', author_string)
    if match:
        return match.group(1).strip()
    return "Unknown"


def build_reason(role_result, ownership_result, theme_names, specificity_score, total_score):
    """
    Builds a plain-language explanation of why this record was surfaced.
    This is what a human reviewer reads to decide whether to act on a signal.
    """
    parts = []

    # Role
    tier = role_result["tier"]
    if tier in ("executive", "vp", "director"):
        parts.append(
            f"Author appears to be a {tier}-level HR decision-maker "
            f"(matched on: '{role_result['matched_on']}')."
        )
    elif tier == "practitioner":
        parts.append("Author appears to be an HR practitioner — not a senior decision-maker, but directly in the hiring process.")
    elif tier == "analyst":
        parts.append("Author appears to be an analyst or journalist — third-party reporting, not first-hand pain.")
    else:
        parts.append("Author role could not be determined.")

    # Ownership
    if ownership_result["ownership_hits"] > 0 and ownership_result["distancing_hits"] == 0:
        parts.append("Strong first-person ownership language detected — author is describing their own situation.")
    elif ownership_result["ownership_hits"] > 0:
        parts.append("Mixed ownership signals — some first-person language but also some distancing phrases.")
    else:
        parts.append("No ownership language detected — author appears to be reporting on others' pain, not their own.")

    # Themes
    themes_readable = ", ".join(t.replace("_", " ") for t in theme_names)
    parts.append(f"Pain themes detected: {themes_readable}.")

    # Specificity
    if specificity_score >= 18:
        parts.append("High specificity — author used concrete numbers, timeframes, or named outcomes.")
    elif specificity_score >= 8:
        parts.append("Moderate specificity — some concrete detail present.")
    else:
        parts.append("Low specificity — pain expressed in general terms without measurable detail.")

    # Verdict
    if total_score >= 75:
        parts.append("Overall: strong signal. Senior author, owns the problem, specific about the pain.")
    elif total_score >= 50:
        parts.append("Overall: moderate signal. Worth monitoring but not high-intent.")
    else:
        parts.append("Overall: weak signal. Likely noise — observer reporting, not decision-maker in pain.")

    return " ".join(parts)