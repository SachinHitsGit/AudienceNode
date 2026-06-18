from enum import unique
import sqlite3
import sqlite3
import sys
import json
import re
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


db_path = "/home/sachinkumar/Desktop/sponser_proof_gen/twitch_chat.db"

import sqlite3

# ── CONFIG ─────────────────────────────────────────────────────────────────────

DB_PATH = "/home/sachinkumar/Desktop/sponser_proof_gen/twitch_chat.db"

# Poll window — change these before each run
# Format: "YYYY-MM-DD HH:MM:SS"
POLL_START = "2024-01-01 00:00:00"
POLL_STOP  = "2099-01-01 00:00:00"  # wide open until you have real timestamps

# Sponsor keywords — whatever the streamer types in
SPONSOR_KEYWORDS = ["nordvpn", "vpn", "discount", "code", "privacy", "sponsor"]


# ── SLANG NORMALIZATION ─────────────────────────────────────────────────────────
# Maps raw Twitch slang to clean sentiment-readable words
# VADER understands "great" and "awful" — it does not understand "PogChamp"

SLANG_MAP = {
    # Positive
    r"\bpog(champ)?\b":     "amazing",
    r"\bpoggers\b":         "amazing",
    r"\bhype\b":            "excited",
    r"\blet(s)?[\s]?go+\b": "great",
    r"\bgg\b":              "great",
    r"\bgoat\b":            "greatest",
    r"\bbanger\b":          "excellent",
    r"\bfire\b":            "excellent",
    r"\bw\b":               "win",
    r"\bop\b":              "overpowered",
    r"\blmao+\b":           "funny",
    r"\blmfao\b":           "funny",
    r"\blol+\b":            "funny",
    r"\bkekw\b":            "funny",
    r"\blul\b":             "funny",
    r"\bkek\b":             "funny",
    r"\bhaha\b":            "funny",
    r"\bhehe\b":            "funny",
    r"\bomg\b":             "surprised",
    r"\bwow+\b":            "surprised",
    r"\bbased\b":           "respectable",
    r"\bslay\b":            "excellent",
    r"\bfr\b":              "seriously",
    r"\bfr fr\b":           "seriously",
    r"\bngl\b":             "honestly",
    r"\bnpc\b":             "boring",

    # Negative
    r"\bl+\b":              "loss",
    r"\bl ratio\b":         "bad",
    r"\bbruh\b":            "disappointed",
    r"\bsmh\b":             "disappointed",
    r"\bnah+\b":            "no",
    r"\bnaah+\b":           "no",
    r"\bnope\b":            "no",
    r"\bcringe\b":          "embarrassing",
    r"\bscuffed\b":         "broken",
    r"\btilted\b":          "frustrated",
    r"\braged?\b":          "angry",
    r"\btoxic\b":           "harmful",
    r"\bskip\b":            "ignore",
    r"\bskipppable\b":      "ignore",

    # Neutral / filler (strip these — they add no signal)
    r"\bpeepo\w*\b":        "",
    r"\bmonka\w*\b":        "",
    r"\bkappa\b":           "",
    r"\bvohi\w*\b":         "",
    r"\b[a-z]?\d+\b":       "",   # stray numbers
}

def normalize_slang(text: str) -> str:
    text = text.lower().strip()
    for pattern, replacement in SLANG_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── STEP 1: FETCH RAW MESSAGES IN POLL WINDOW ──────────────────────────────────

def fetch_raw_messages(conn, start: str, stop: str) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message
        FROM chat_logs
        WHERE timestamp BETWEEN ? AND ?
    """, (start, stop))
    rows = cursor.fetchall()
    return [{"raw": row[0], "clean": normalize_slang(row[0])} for row in rows if row[0]]


# ── STEP 2: SQL COMPRESSION ────────────────────────────────────────────────────

def compress_messages(conn, start: str, stop: str) -> list[dict]:
    """
    Groups identical normalized messages and counts them as weight.
    Returns list of {message, weight} sorted by weight descending.
    """
    raw = fetch_raw_messages(conn, start, stop)
    if not raw:
        return []

    # Group by cleaned message in Python (SQLite doesn't have our normalization)
    counts: dict[str, int] = {}
    for item in raw:
        clean = item["clean"]
        if clean:  # skip empty strings after normalization
            counts[clean] = counts.get(clean, 0) + 1

    compressed = [
        {"message": msg, "weight": w}
        for msg, w in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]
    return compressed


# ── STEP 3: SPONSOR KEYWORD SCORE ─────────────────────────────────────────────

def sponsor_keyword_score(conn, start: str, stop: str, keywords: list[str]) -> dict:
    """
    Scans raw messages in the poll window for sponsor keywords.
    Returns recall % and per-keyword breakdown.
    """
    cursor = conn.cursor()

    # Total message count in window
    cursor.execute("""
        SELECT COUNT(*) FROM chat_logs
        WHERE timestamp BETWEEN ? AND ?
    """, (start, stop))
    total = cursor.fetchone()[0]

    if total == 0:
        return {"total_messages": 0, "recall_percent": 0.0, "keyword_hits": {}}

    keyword_hits = {}
    messages_with_any_keyword = set()

    for keyword in keywords:
        pattern = f"%{keyword.lower()}%"
        cursor.execute("""
            SELECT rowid, message FROM chat_logs
            WHERE timestamp BETWEEN ? AND ?
            AND LOWER(message) LIKE ?
        """, (start, stop, pattern))
        hits = cursor.fetchall()
        keyword_hits[keyword] = len(hits)
        for row in hits:
            messages_with_any_keyword.add(row[0])

    recall_percent = round((len(messages_with_any_keyword) / total) * 100, 2)

    return {
        "total_messages": total,
        "messages_mentioning_sponsor": len(messages_with_any_keyword),
        "recall_percent": recall_percent,
        "keyword_hits": keyword_hits,
    }


# ── STEP 4: WEIGHTED SENTIMENT SCORE ──────────────────────────────────────────

def weighted_sentiment(compressed: list[dict]) -> dict:
    """
    Runs VADER on each unique cleaned message.
    Weights the result by how many times that message appeared.
    Returns % positive, neutral, negative.
    """
    analyzer = SentimentIntensityAnalyzer()

    total_weight = 0
    positive_weight = 0
    neutral_weight  = 0
    negative_weight = 0

    for item in compressed:
        msg    = item["message"]
        weight = item["weight"]
        score  = analyzer.polarity_scores(msg)
        compound = score["compound"]

        total_weight += weight

        if compound >= 0.05:
            positive_weight += weight
        elif compound <= -0.05:
            negative_weight += weight
        else:
            neutral_weight += weight

    if total_weight == 0:
        return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

    return {
        "positive": round((positive_weight / total_weight) * 100, 2),
        "neutral":  round((neutral_weight  / total_weight) * 100, 2),
        "negative": round((negative_weight / total_weight) * 100, 2),
    }


# ── STEP 5: ASSEMBLE FINAL JSON OUTPUT ────────────────────────────────────────

def run_pipeline(
    db_path: str,
    poll_start: str,
    poll_stop: str,
    sponsor_keywords: list[str]
)-> dict :
    conn = sqlite3.connect(db_path)
    print("Fetching and commpressing messages...")
    
    compressed = compress_messages(conn, poll_start, poll_stop)
    print(f"    -> {sum(c['weight'] for c in compressed)} raw messages compressed t {len(compressed)} unique strings")
    
    print("Running sponser keyword scan...")
    keyword_results = sponsor_keyword_score(conn, poll_start, poll_stop, sponsor_keywords)

    print("Running weighted sentiment analysis...")
    sentiment_results = weighted_sentiment(compressed)

    conn.close()

    output = {
        "meta": {
            "poll_start": poll_start,
            "poll_stop": poll_stop,
            "generated_at": datetime.utcnow().isoformat(),
            "sponsor_keywords": sponsor_keywords,
        },
        "summary": {
            "total_messages": keyword_results["total_messages"],
            "unique_messages": len(compressed),
            "compression_ratio": round(
                keyword_results["total_messages"] / max(len(compressed), 1), 1
                ),

        },
        "sponsor_recall": keyword_results,
        "sentiment": sentiment_results,
        "top_messages": compressed[:20]
    }

    return output


# ── RUN ────────────────────────────────────────────────────────────────────────

def run_sponser_pipeline(start_time: str, stop_time: str, keywords: list[str] = None):
    if keywords is None:
        keywords = ["nordvpn", "vpn", "discount", "code", "privacy", "sponsor"]
    
    return run_pipeline(
        db_path=DB_PATH,
        poll_start=start_time,
        poll_stop=stop_time,
        sponsor_keywords=keywords
    )

if __name__== "__main__":
    result = run_sponser_pipeline(POLL_START, POLL_STOP, SPONSOR_KEYWORDS)
    print("\n Pipeline Complete - json output.")
    print(json.dumps(result, indent=2))