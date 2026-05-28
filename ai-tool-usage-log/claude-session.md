# Claude Session Log — Vikaas Signal Detector

**Tool:** Claude (Anthropic)  
**Task:** Track 3 — Hiring Pain / Intent Detector  
**Date:** May 2026

---

## What Claude helped with

- Designed the four-dimension scoring model structure (role, ownership, theme, specificity)
- Wrote the ownership language regex patterns and distancing phrase patterns
- Wrote the README scaffolding including scoring logic tables and limitations section
- Suggested Google News RSS as a workaround for LinkedIn's auth wall
- Identified the DB accumulation bug (init_db not dropping table before recreating)

## What I did

- Designed and wrote the RSS source list and selected which publications to target
- Wrote all demo entries in `get_demo_entries()` — constructed to represent realistic LinkedIn-style posts across different role tiers
- Caught that `output/` was gitignored despite the submission checklist explicitly requiring sample output — corrected this before pushing
- Verified live mode behavior: confirmed that scoring Recruiting Daily content at 18–38 due to zero ownership language is correct behavior, not a bug
- Read and understood every module before moving to the next — able to defend all scoring decisions

## What I can defend

- Every scoring dimension: why 0–25, what a score of 95 vs 28 means in practice
- Why LinkedIn was excluded and documented as a limitation rather than worked around with fake data
- Why first-person ownership language is the core discriminator between signal and noise
- The role false-positive bug (analyst pieces inflated by title text matching) — spotted it in live output, documented it honestly in README
- Why RSS over scraping: stability and compliance over speed

## Lines I would change with more time

- Role detection scope: currently scans full text, should be restricted to author byline only
- Temporal decay on signal score for older posts
- NLP-based ownership detection to catch paraphrased first-person language
