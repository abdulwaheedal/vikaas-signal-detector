# Vikaas Signal Detector

A hiring pain signal detector that identifies public expressions of genuine hiring distress from HR decision-makers — and distinguishes them from third-party industry reporting.

---

## Setup and Run

**Requirements:** Python 3.x, pip

```bash
git clone https://github.com/abdulwaheedal/vikaas-signal-detector.git
cd vikaas-signal-detector
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run with sample data (no network required)

```bash
python3 handler.py --demo
```

### Run against live RSS feeds

```bash
python3 handler.py --live
```

### Run live with full article text (slower, higher accuracy)

```bash
python3 handler.py --live --full-text
```

### Filter to high-confidence signals only

```bash
python3 handler.py --demo --min-score 70
```

Output is written to:

```text
output/signals.json
output/signals.db
```

---

# Data Ingestion Approach

## Sources Used

### HR Dive

`hrdive.com/feeds/news/`

Trade publication covering HR news. Used because it consistently publishes articles that surface practitioner quotes.

**Limitation:** paywalled articles return 403s, so full-text fetch is partial.

### Recruiting Daily

`recruitingdaily.com/feed/`

Practitioner-focused publication with bylined posts from working recruiters. More likely than HR Dive to include first-person language from people in hiring roles.

### SHRM and ERE Media

Attempted but both returned malformed feeds at time of build. Left in the source list with graceful skip handling so they can be re-enabled.

### Google News RSS

Highly configurable tracking feeds specifically tuned to 2026 search operators (e.g. `"CHRO hiring challenges 2026"`). This surfaces broader mainstream business coverage.

### Medium Tags (Recruiting & Talent Acquisition)

It was added to surface first-person practitioner blogs and case studies. These feeds bypass standard WAF blocks and are significantly more likely to contain the "I/we/my team" ownership language required to trigger a high-intent signal.

---

## What I Had to Work Around

### LinkedIn is the ideal source

HR leaders posting about their own hiring pain in first-person is the highest-signal data available.

LinkedIn does not allow unauthenticated scraping. Every public post URL requires a login redirect.

I made a deliberate choice not to fake LinkedIn data or simulate it as if the system could access it.

The demo entries are constructed to represent what LinkedIn posts would look like if they were accessible, but the live system does not pretend to fetch them.

### HR Dive blocks full-text fetching with 403 errors

The system handles this gracefully — if full text is unavailable, it falls back to the RSS summary.

This reduces accuracy but does not break the run.

---

## Why RSS Over Scraping

RSS feeds are structured, stable, and terms-of-service compliant.

Scraping article pages directly would be faster to build but fragile. One layout change breaks the scraper.

RSS degrades gracefully.

---

# Scoring Logic

Every signal is scored across four independent dimensions, each `0–25`, for a total of `0–100`.

---

## Dimension 1: Role Authority (0–25)

Who is speaking?

| Role Tier             | Score | Example                               |
| --------------------- | ----- | ------------------------------------- |
| Executive (CHRO, CPO) | 25    | "Sarah Chen, CHRO at Meridian Health" |
| VP-level              | 20    | "VP of Talent Acquisition"            |
| Director / Head of    | 15    | "Head of Recruiting"                  |
| Practitioner          | 10    | "Senior Recruiter"                    |
| Analyst / Editorial   | 3     | "HR Dive Staff"                       |
| Unknown               | 0     | No byline                             |

A CHRO describing a problem has purchasing authority. A recruiter describing the same problem does not.

The score reflects that difference.

---

## Dimension 2: Ownership Language (0–25)

Is the author inside the pain or reporting on it from outside?

This is the core signal vs noise discriminator.

### Scoring

- Each first-person ownership phrase match (`our process`, `my team`, `we lost`) adds `+5`
- Each distancing phrase (`companies struggle`, `analysts note`, `research shows`) subtracts `-3`
- Score is clamped to `0–25`

### Examples

A CHRO writing:

> "our offer acceptance rate dropped from 84% to 61%"

scores `25`.

An analyst writing:

> "talent acquisition teams report declining acceptance rates"

scores `0`.

This single dimension correctly separates the two cases the brief identifies as the core insight.

---

## Dimension 3: Theme Presence (0–25)

Is a real pain theme actually present?

### Five themes are detected

- `interview_speed`
- `recruiter_overload`
- `inconsistent_evaluation`
- `hiring_quality`
- `time_to_hire_pressure`

### Scoring behavior

- `0 themes detected` → record is dropped entirely, not scored
- `1 theme` → half the theme's base score (topic present but may be shallow)
- `2+ themes` → full base score of strongest theme (author is immersed in the problem)

---

## Dimension 4: Specificity (0–25)

Are there concrete details or is the pain vague?

| Signal                                           | Points |
| ------------------------------------------------ | ------ |
| Percentages or numeric rates                     | +8     |
| Specific counts (`three finalists`, `240 roles`) | +7     |
| Named timeframes (`last month`, `in Q3`)         | +6     |
| Company or team size context                     | +4     |

"Hiring is hard" scores `0`.

"We lost three finalists last month because our process takes six weeks"

scores `13` on this dimension alone.

---

# Score Interpretation

| Range  | Meaning                                                                                   |
| ------ | ----------------------------------------------------------------------------------------- |
| 75–100 | Strong signal. Senior decision-maker, owns the problem, quantified pain. Worth acting on. |
| 50–74  | Moderate signal. Real topic, some ownership, worth monitoring.                            |
| 25–49  | Weak signal. Pain theme present but author is likely observing, not experiencing.         |
| 0–24   | Noise. Detected only because keywords matched — context does not support it as a signal.  |

---

# What the Score Cannot Capture

The score cannot determine recency of the pain.

A post from 18 months ago might describe a problem that's already been solved.

The score cannot detect sarcasm or irony.

It cannot distinguish a CHRO who has already purchased a solution from one who is actively looking.

These would require NLP capabilities beyond keyword and pattern matching.

---

# Assumptions and Limitations

## What I Assumed Was True That Might Not Be

- That author bylines in RSS feeds accurately reflect the person's actual role.
- Many RSS feeds omit author entirely or list the publication name.
- A post by a CHRO published on HR Dive might be attributed to `"HR Dive Staff"` and score incorrectly as analyst-tier.

- That first-person ownership language reliably indicates the author is in pain rather than writing a case study about a past problem they've already solved.
- The system cannot distinguish:
  - `"we struggled with this last year"`
  - from
  - `"we are struggling with this right now"`

- That trade publications are lower-signal than LinkedIn posts.
- This is directionally correct but not absolute — some SHRM bylined pieces are written directly by CHROs describing their own challenges.

---

## What the System Gets Wrong

The role detector has a known false-positive:

It scans the article title and summary for role keywords, not just the author byline.

An article titled:

> "Talent acquisition teams report rising pressure"

will score the author as practitioner-tier because `"talent acquisition"` appears in the text.

This inflates the role score for analyst pieces.

It is visible in live output:

> HR Dive Staff scored `role=10` despite being editorial staff.

### Proper Fix

Restrict role detection to:

- author field only
- first sentence of the article

not the full text.

This was not implemented due to time constraints.

---

# What I Would Fix First With More Time

- **Role detection scope**
  - Restrict to author byline and article opening sentence only

- **LinkedIn access**
  - The highest-signal source is completely inaccessible without auth
  - A production version would use LinkedIn's official API with proper credentials
  - Or a monitoring service like Mention or Brandwatch that has compliant access

- **Temporal decay**
  - Signals older than 30 days should have their score reduced
  - The pain may already have been addressed

- **NLP ownership detection**
  - The current regex approach misses paraphrased ownership language
  - A lightweight classifier trained on positive/negative examples would significantly improve ownership scoring

- **Bypassing Web Application Firewalls (WAFs)**
  - Enterprise trade publications like HR Dive utilize aggressive Cloudflare protections
  - Standard HTTP requests often receive `403 Forbidden`
  - A production version would replace the basic fetcher with:
    - Playwright Stealth
    - automated browser pools
    - residential proxy infrastructure
