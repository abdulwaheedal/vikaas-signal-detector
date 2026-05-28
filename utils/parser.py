import re

# Role hierarchy — higher tier = more decision-making authority
# This is what separates a CHRO's post from an analyst's report
ROLE_TIERS = {
    "executive": {
        "score": 25,
        "keywords": [
            "chro", "chief human resources", "chief people officer",
            "chief hr", "cpo", "chief talent"
        ],
    },
    "vp": {
        "score": 20,
        "keywords": [
            "vp of talent", "vp talent", "vp of hr", "vp hr",
            "vp of people", "vp people", "vice president of talent",
            "vice president of hr", "vice president talent"
        ],
    },
    "director": {
        "score": 15,
        "keywords": [
            "head of recruiting", "head of talent", "head of hr",
            "head of people", "director of talent", "director of hr",
            "director of recruiting", "director of people",
            "director, talent", "director, hr"
        ],
    },
    "practitioner": {
        "score": 10,
        "keywords": [
            "recruiter", "talent acquisition", "hr manager",
            "hr business partner", "hrbp", "recruiting manager",
            "hiring manager", "people ops", "people operations"
        ],
    },
    "analyst": {
        "score": 3,
        "keywords": [
            "analyst", "researcher", "editor", "staff writer",
            "journalist", "contributor", "correspondent",
            "editorial", "report", "survey"
        ],
    },
}

# First-person ownership phrases — these are the core signal discriminator.
# "Our process takes 6 weeks" means the author IS in the pain.
# "Companies struggle with long processes" means they're observing it.
OWNERSHIP_PHRASES = [
    r"\bour\s+(hiring|interview|process|team|recruiter|pipeline|ATS|offer|onboard)",
    r"\bmy\s+(team|recruiter|hiring|process|pipeline|manager|req)",
    r"\bwe\s+(lost|lose|missed|dropped|ghosted|failed|struggle|can't|cannot|need)",
    r"\bwe('ve| have)\s+(been|seen|had|made|tried|watched)",
    r"\bi('ve| have)\s+(been|seen|had|made|tried|watched|asked|built|run)",
    r"\bour\s+(offer acceptance|acceptance rate|time.to.hire|attrition|turnover)",
    r"\bI\s+need\s+to\b",
    r"\bI('m| am)\s+(building|fixing|trying|watching|asking|running)",
]

# Third-person distancing phrases — these suggest an observer, not a participant
DISTANCING_PHRASES = [
    r"\bcompanies\s+(struggle|report|face|find|are)",
    r"\borganizations\s+(struggle|report|face|find|are)",
    r"\bteams\s+report\b",
    r"\bindustry\s+(data|report|trend|survey|observer)",
    r"\bexperts\s+(suggest|note|say|recommend)",
    r"\baccording\s+to\b",
    r"\banalysts\s+(note|say|suggest|find)",
    r"\bresearch\s+(shows|suggests|finds|indicates)",
    r"\bsurvey\s+(shows|finds|reveals|indicates)",
]


def detect_author_role(author_string, full_text=""):
    """
    Detects the role tier of the author.
    Checks the author byline first, then scans the article text
    for role mentions (e.g. "As CHRO at...").

    Returns a dict: { "tier": str, "score": int, "matched_on": str }
    """
    combined = (author_string + " " + full_text[:500]).lower()

    for tier_name, tier_data in ROLE_TIERS.items():
        for keyword in tier_data["keywords"]:
            if keyword in combined:
                return {
                    "tier": tier_name,
                    "score": tier_data["score"],
                    "matched_on": keyword,
                }

    return {
        "tier": "unknown",
        "score": 0,
        "matched_on": None,
    }


def score_ownership_language(text):
    """
    Scores how much first-person ownership language appears vs distancing language.

    Returns a dict:
    {
        "score": int (0-25),
        "ownership_hits": list of matched phrases,
        "distancing_hits": list of matched phrases
    }

    Logic:
    - Each ownership phrase match = +5 (capped at 25)
    - Each distancing phrase match = -3 (floor at 0)
    - Net score is what goes into the signal record
    """
    ownership_hits = []
    distancing_hits = []

    for pattern in OWNERSHIP_PHRASES:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            ownership_hits.append(pattern)

    for pattern in DISTANCING_PHRASES:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            distancing_hits.append(pattern)

    raw_score = (len(ownership_hits) * 5) - (len(distancing_hits) * 3)
    clamped_score = max(0, min(25, raw_score))

    return {
        "score": clamped_score,
        "ownership_hits": len(ownership_hits),
        "distancing_hits": len(distancing_hits),
    }


def extract_matched_keywords(text, keyword_list):
    """
    Returns a deduplicated list of keywords from keyword_list
    that appear in text. Case-insensitive.
    Used to populate the matched_keywords field in the output record.
    """
    text_lower = text.lower()
    return list({kw for kw in keyword_list if kw.lower() in text_lower})


def build_full_text(entry):
    """
    Combines title + summary + any fetched article body
    into one string for analysis.
    """
    parts = [
        entry.get("title", ""),
        entry.get("summary", ""),
        entry.get("article_text", ""),
    ]
    return " ".join(p for p in parts if p)