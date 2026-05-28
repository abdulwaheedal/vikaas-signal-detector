import argparse
import json
import sqlite3
import os
from datetime import datetime, timezone

from utils.fetcher import get_demo_entries, fetch_rss_feeds, fetch_article_text
from signals.scorer import compute_signal


OUTPUT_DIR = "output"
JSON_PATH = os.path.join(OUTPUT_DIR, "signals.json")
DB_PATH = os.path.join(OUTPUT_DIR, "signals.db")


def init_db(conn):
    conn.execute("DROP TABLE IF EXISTS signals")
    conn.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            signal_type TEXT,
            source_url TEXT,
            matched_keywords TEXT,
            signal_score INTEGER,
            detected_at TEXT,
            reason TEXT
        )
    """)
    conn.commit()


def save_to_db(conn, record):
    conn.execute("""
        INSERT INTO signals
        (company, signal_type, source_url, matched_keywords,
         signal_score, detected_at, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        record["company"],
        record["signal_type"],
        record["source_url"],
        json.dumps(record["matched_keywords"]),
        record["signal_score"],
        record["detected_at"],
        record["reason"],
    ))
    conn.commit()


def clean_record(record):
    """Strip debug fields before writing to final output."""
    return {k: v for k, v in record.items() if not k.startswith("_")}


def run(mode="demo", min_score=0, fetch_full_text=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load entries
    if mode == "demo":
        print("[handler] Running in DEMO mode — using sample data, no network calls.")
        entries = get_demo_entries()
    else:
        print("[handler] Running in LIVE mode — fetching from RSS feeds.")
        entries = fetch_rss_feeds(max_per_feed=10)

        if fetch_full_text:
            print("[handler] Processing article text (Full Text or Fallback)...")
        for entry in entries:
            # 1. Base Fallback: Combine title and summary
            fallback_text = f"{entry.get('title', '')} {entry.get('summary', '')}"
            entry["article_text"] = fallback_text 
            
            # 2. Try full text if requested
            if fetch_full_text and entry.get("url"):
                full_text = fetch_article_text(entry["url"])
                # If we successfully bypassed the firewall and got text, overwrite the fallback
                if full_text and len(full_text.strip()) > 0:
                    entry["article_text"] = full_text
                else:
                    print(f"  -> [Fallback] Blocked by WAF or empty text. Using RSS metadata.")

    # Score each entry
    signals = []
    skipped = 0

    for entry in entries:
        result = compute_signal(entry)
        if result is None:
            skipped += 1
            continue
        if result["signal_score"] < min_score:
            skipped += 1
            continue
        signals.append(result)

    # Sort by score descending
    signals.sort(key=lambda x: x["signal_score"], reverse=True)

    # Write JSON output
    clean_signals = [clean_record(s) for s in signals]
    with open(JSON_PATH, "w") as f:
        json.dump(clean_signals, f, indent=2)
    print(f"[handler] Wrote {len(clean_signals)} signals to {JSON_PATH}")

    # Write SQLite output
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    for record in clean_signals:
        save_to_db(conn, record)
    conn.close()
    print(f"[handler] Wrote {len(clean_signals)} signals to {DB_PATH}")

    # Print summary to terminal
    print(f"\n{'='*60}")
    print(f"  SIGNAL SUMMARY  |  mode={mode}  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print(f"  Entries processed : {len(entries)}")
    print(f"  Signals detected  : {len(signals)}")
    print(f"  Skipped (no theme or below min_score): {skipped}")
    print(f"{'='*60}\n")

    for s in signals:
        debug = s.get("_debug", {})
        print(f"  [{s['signal_score']:>3}]  {s['signal_type']:<30}  {debug.get('author','')[:45]}")
        print(f"         role={debug.get('role_score')}  "
              f"ownership={debug.get('ownership_score')}  "
              f"theme={debug.get('theme_score')}  "
              f"specificity={debug.get('specificity_score')}")
        print(f"         {s['source_url'][:70]}")
        print()

    print(f"\nFull output: {JSON_PATH}")
    return signals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vikaas Signal Detector")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with sample data only, no network calls"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Fetch real data from RSS feeds"
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=0,
        help="Only output signals above this score (default: 0)"
    )
    parser.add_argument(
        "--full-text",
        action="store_true",
        help="Fetch full article body for each entry (slower, more accurate)"
    )
    args = parser.parse_args()

    if args.live:
        run(mode="live", min_score=args.min_score, fetch_full_text=args.full_text)
    else:
        run(mode="demo", min_score=args.min_score)