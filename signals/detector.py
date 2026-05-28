import re

# The five pain themes from the brief.
# Each has a keyword list and a base theme score.
# Keywords are chosen to be specific enough to avoid false positives —
# "slow" alone isn't a signal, "interview loop takes" is closer.

PAIN_THEMES = {
    "interview_speed": {
        "base_score": 20,
        "keywords": [
            "interview loop", "interview process takes", "six week", "six-week",
            "four week", "four-week", "eight week", "weeks to hire",
            "too many rounds", "too many interviews", "nine steps", "multiple rounds",
            "process too long", "slow process", "lengthy process",
            "candidates dropping", "candidates ghosting", "ghosted after",
            "offer stage dropout", "lost finalist", "lost candidates",
        ],
    },
    "recruiter_overload": {
        "base_score": 20,
        "keywords": [
            "open reqs", "open requisitions", "reqs per recruiter",
            "recruiter capacity", "recruiter bandwidth", "overwhelmed recruiter",
            "understaffed", "too many roles", "not enough recruiters",
            "recruiter burnout", "response time slipped", "slow to respond",
            "can't respond fast enough", "handling too many",
            "headcount request", "asked for headcount",
        ],
    },
    "inconsistent_evaluation": {
        "base_score": 18,
        "keywords": [
            "inconsistent interview", "no structured interview",
            "unstructured interview", "every manager interviews differently",
            "hiring manager inconsistency", "no rubric", "no scorecard",
            "subjective hiring", "gut feel hiring", "different criteria",
            "no standard process", "interview varies", "case question",
            "culture fit vague", "bad hire", "wrong hire", "mis-hire",
            "hiring quality", "poor hiring decision",
        ],
    },
    "hiring_quality": {
        "base_score": 18,
        "keywords": [
            "bad hire", "wrong hire", "mis-hire", "quality of hire",
            "hire didn't work out", "failed hire", "regrettable hire",
            "poor performance after hire", "attrition after hire",
            "early attrition", "churned within", "left within 90",
            "hiring mistake", "wrong person", "cultural mismatch",
        ],
    },
    "time_to_hire_pressure": {
        "base_score": 20,
        "keywords": [
            "time to hire", "time-to-hire", "days to fill", "time to fill",
            "offer acceptance rate", "acceptance rate dropped",
            "competing offers", "lost to competitor", "competing with",
            "faster than us", "responded faster", "q3 hiring", "q4 hiring",
            "hiring deadline", "headcount plan", "hiring target",
            "pressure to hire", "need to hire fast", "backfill",
        ],
    },
}


def detect_themes(text):
    """
    Scans text for pain theme keywords.
    Returns a list of detected theme dicts, each with:
    - theme_name
    - matched_keywords: which specific keywords fired
    - base_score: the theme's weight

    A piece of text can match multiple themes — that's realistic
    (a CHRO post about a slow process often touches both
    interview_speed and time_to_hire_pressure).
    """
    text_lower = text.lower()
    detected = []

    for theme_name, theme_data in PAIN_THEMES.items():
        matched = [
            kw for kw in theme_data["keywords"]
            if kw.lower() in text_lower
        ]
        if matched:
            detected.append({
                "theme_name": theme_name,
                "matched_keywords": matched,
                "base_score": theme_data["base_score"],
            })

    return detected


def score_themes(detected_themes):
    """
    Converts detected themes into a single 0-25 theme score.

    Logic:
    - 0 themes detected = 0
    - 1 theme = half its base score (topic present but may be shallow)
    - 2+ themes = full base score of strongest theme
      (multiple themes = the author is immersed in the problem space)

    Capped at 25.
    """
    if not detected_themes:
        return 0

    best_score = max(t["base_score"] for t in detected_themes)

    if len(detected_themes) == 1:
        raw = best_score * 0.5
    else:
        raw = best_score

    return min(25, int(raw))


def score_specificity(text):
    """
    Scores how specific and grounded the pain expression is.
    Vague pain ("hiring is hard") scores low.
    Specific pain ("our offer acceptance dropped from 84% to 61%") scores high.

    Signals we look for:
    - Exact numbers or percentages
    - Named timeframes ("last month", "this quarter", "in Q3")
    - Concrete outcomes ("lost 3 finalists", "3 bad hires")
    - Named team sizes or role counts

    Returns an int 0-25.
    """
    score = 0

    # Percentages or numeric rates
    if re.search(r'\d+\s*%', text):
        score += 8

    # Specific counts (e.g. "three finalists", "6 recruiters", "240 roles")
    if re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+'
                 r'(finalists?|candidates?|hires?|roles?|reqs?|recruiters?|'
                 r'steps?|rounds?|weeks?|days?|months?|bad hires?)\b', text, re.IGNORECASE):
        score += 7

    # Named timeframes
    if re.search(r'\b(last month|this quarter|last quarter|in q[1-4]|'
                 r'this year|last year|past \d+ months?|within \d+ days?)\b',
                 text, re.IGNORECASE):
        score += 6

    # Named team or company size context
    if re.search(r'\b(\d+.person|\d+.employee|series [abcde]|'
                 r'team of \d+|company of \d+)\b', text, re.IGNORECASE):
        score += 4

    return min(25, score)


def get_all_matched_keywords(detected_themes):
    """
    Flattens matched keywords across all detected themes
    into a single deduplicated list.
    Used for the matched_keywords field in the output record.
    """
    all_kw = []
    for theme in detected_themes:
        all_kw.extend(theme["matched_keywords"])
    return list(set(all_kw))