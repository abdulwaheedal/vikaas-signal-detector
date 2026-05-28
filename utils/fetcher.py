import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

# These are the RSS feeds we pull from.
# Each has a credibility_tier: 1 = practitioner-authored (higher signal potential),
# 2 = trade publication (mixed), 3 = analyst/news (lower signal potential)
RSS_SOURCES = [
    {
        "name": "HR Dive",
        "url": "https://www.hrdive.com/feeds/news/",
        "credibility_tier": 2,
    },
    {
        "name": "Recruiting Daily",
        "url": "https://recruitingdaily.com/feed/",
        "credibility_tier": 2,
    },
    {
        "name": "Google News - CHRO hiring",
        "url": "https://news.google.com/rss/search?q=CHRO+hiring+challenges+2025&hl=en-US&gl=US&ceid=US:en",
        "credibility_tier": 1,
    },
    {
        "name": "Google News - VP talent pain",
        "url": "https://news.google.com/rss/search?q=VP+talent+acquisition+interview+process&hl=en-US&gl=US&ceid=US:en",
        "credibility_tier": 1,
    },
    {
        "name": "Google News - head of recruiting",
        "url": "https://news.google.com/rss/search?q=head+of+recruiting+hiring+process+slow&hl=en-US&gl=US&ceid=US:en",
        "credibility_tier": 1,
    },
    {
        "name": "Medium - Recruiting",
        "url": "https://medium.com/feed/tag/recruiting",
        "credibility_tier": 2,
    },
    {
        "name": "Medium - Talent Acquisition",
        "url": "https://medium.com/feed/tag/talent-acquisition",
        "credibility_tier": 2,
    }
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}


def fetch_rss_feeds(max_per_feed=10):
    """
    Pulls entries from all RSS sources.
    Returns a flat list of raw entry dicts.
    Skips any feed that fails — one dead feed shouldn't kill the run.
    """
    all_entries = []

    for source in RSS_SOURCES:
        print(f"[fetcher] Fetching: {source['name']}")
        try:
            feed = feedparser.parse(source["url"])

            if feed.bozo and not feed.entries:
                print(f"[fetcher] WARNING: {source['name']} returned a malformed feed, skipping.")
                continue

            for entry in feed.entries[:max_per_feed]:
                raw = {
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "url": entry.get("link", ""),
                    "author": entry.get("author", ""),
                    "published": entry.get("published", ""),
                    "source_name": source["name"],
                    "credibility_tier": source["credibility_tier"],
                }
                all_entries.append(raw)

            print(f"[fetcher] Got {min(len(feed.entries), max_per_feed)} entries from {source['name']}")

        except Exception as e:
            print(f"[fetcher] ERROR on {source['name']}: {e}")
            continue

    return all_entries


def fetch_article_text(url, timeout=8):
    """
    Fetches the full text of an article given its URL.
    Returns plain text string, or empty string on failure.
    We grab full text because RSS summaries are often truncated —
    and ownership language ("our team", "we lost") tends to appear
    in the body, not the headline.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Remove nav, footer, ads — we want article body only
        for tag in soup(["nav", "footer", "script", "style", "aside", "header"]):
            tag.decompose()

        # Try common article content containers first
        for selector in ["article", "main", ".article-body", ".post-content", ".entry-content"]:
            container = soup.select_one(selector)
            if container:
                return container.get_text(separator=" ", strip=True)

        # Fallback: grab all paragraph text
        paragraphs = soup.find_all("p")
        return " ".join(p.get_text(strip=True) for p in paragraphs)

    except Exception as e:
        print(f"[fetcher] Could not fetch article text for {url}: {e}")
        return ""


def get_demo_entries():
    """
    Hardcoded sample entries for --demo mode.
    Deliberately includes both signals and noise so the scorer
    can demonstrate real differentiation.
    """
    return [
        {
            "title": "We lost three finalists last month because our process takes six weeks",
            "summary": "As CHRO at a 400-person company, I've watched our offer acceptance rate drop from 84% to 61% this year. Our interview loop has nine steps. Candidates are ghosting us after round four. I need to fix this before Q3 hiring kicks off.",
            "url": "https://www.linkedin.com/posts/example-chro-post",
            "author": "Sarah Chen, CHRO at Meridian Health",
            "published": "2025-05-10",
            "source_name": "LinkedIn",
            "credibility_tier": 1,
        },
        {
            "title": "My recruiters are handling 40 open reqs each — something has to change",
            "summary": "VP of Talent Acquisition here. Our team of 6 is trying to fill 240 roles simultaneously. Response times to candidates have slipped to 11 days. I've asked for headcount twice. The answer is no. We're losing people to companies that respond faster.",
            "url": "https://recruitingdaily.com/example-post",
            "author": "James Okafor, VP Talent Acquisition",
            "published": "2025-05-12",
            "source_name": "Recruiting Daily",
            "credibility_tier": 2,
        },
        {
            "title": "Survey: 67% of HR leaders cite time-to-hire as top concern in 2025",
            "summary": "A new industry report from TalentBoard shows that talent acquisition teams across sectors are reporting increasing pressure on hiring velocity. Analysts note that companies are struggling with inconsistent evaluation frameworks.",
            "url": "https://www.hrdive.com/example-survey",
            "author": "HR Dive Staff",
            "published": "2025-05-08",
            "source_name": "HR Dive",
            "credibility_tier": 2,
        },
        {
            "title": "Inconsistent interviews are killing our hiring quality",
            "summary": "Head of Recruiting at a Series B startup. Every hiring manager runs interviews differently. One asks case questions, one does culture chat, one makes candidates build a deck. We've made three bad hires in five months. I'm building a structured interview guide this week whether leadership buys in or not.",
            "url": "https://www.linkedin.com/posts/example-head-recruiting",
            "author": "Priya Nair, Head of Recruiting",
            "published": "2025-05-14",
            "source_name": "LinkedIn",
            "credibility_tier": 1,
        },
        {
            "title": "The state of recruiting technology in 2025",
            "summary": "Industry observers note that recruiting technology adoption continues to accelerate. Talent acquisition teams report challenges with ATS integration and candidate experience. Experts suggest that organizations should evaluate their hiring stack annually.",
            "url": "https://www.ere.net/example-trend-post",
            "author": "ERE Editorial",
            "published": "2025-05-06",
            "source_name": "ERE Media",
            "credibility_tier": 3,
        },
    ]