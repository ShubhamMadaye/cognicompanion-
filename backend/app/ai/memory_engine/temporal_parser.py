"""
CogniCompanion — PME Temporal Parser
====================================
Extracts temporal bounds (start_date, end_date, timeframe, timing)
from patient and caregiver queries to enforce deterministic date filtering.
"""

from dataclasses import dataclass
from datetime import date, timedelta
import re


@dataclass(frozen=True)
class TemporalContext:
    timeframe: str  # "today" | "yesterday" | "tomorrow" | "this_week" | "last_week" | "recent" | "all"
    start_date: date | None
    end_date: date | None
    timing: str | None = None  # "morning" | "afternoon" | "evening" | "night" | None

    @property
    def is_bounded(self) -> bool:
        return self.start_date is not None or self.end_date is not None


def parse_temporal_context(query: str, reference_date: date | None = None) -> TemporalContext:
    """
    Parses temporal indicators in a query into concrete start/end dates.
    """
    today = reference_date or date.today()
    q = query.lower()

    # 1. Timing extraction (time of day)
    timing: str | None = None
    if any(w in q for w in ["morning", "breakfast", "8 am", "9 am", "8:00", "9:00"]):
        timing = "morning"
    elif any(w in q for w in ["afternoon", "lunch", "noon", "1 pm", "2 pm", "12:00"]):
        timing = "afternoon"
    elif any(w in q for w in ["evening", "dinner", "night", "bedtime", "7 pm", "8 pm"]):
        timing = "evening"

    # 2. Date bounds extraction
    if "yesterday" in q:
        target = today - timedelta(days=1)
        return TemporalContext(
            timeframe="yesterday",
            start_date=target,
            end_date=target,
            timing=timing,
        )

    if "tomorrow" in q:
        target = today + timedelta(days=1)
        return TemporalContext(
            timeframe="tomorrow",
            start_date=target,
            end_date=target,
            timing=timing,
        )

    if any(w in q for w in ["last week", "past week", "previous week"]):
        return TemporalContext(
            timeframe="last_week",
            start_date=today - timedelta(days=14),
            end_date=today - timedelta(days=7),
            timing=timing,
        )

    if any(w in q for w in ["this week", "past 7 days", "last 7 days", "last few days"]):
        return TemporalContext(
            timeframe="this_week",
            start_date=today - timedelta(days=7),
            end_date=today,
            timing=timing,
        )

    if any(w in q for w in ["recently", "recent", "lately"]):
        return TemporalContext(
            timeframe="recent",
            start_date=today - timedelta(days=3),
            end_date=today,
            timing=timing,
        )

    if "today" in q or "now" in q or "tonight" in q or "this morning" in q or "this evening" in q:
        return TemporalContext(
            timeframe="today",
            start_date=today,
            end_date=today,
            timing=timing,
        )

    # Specific ISO-like or written date formats (e.g., 2026-09-20)
    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", q)
    if iso_match:
        try:
            d = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
            return TemporalContext(
                timeframe=d.isoformat(),
                start_date=d,
                end_date=d,
                timing=timing,
            )
        except ValueError:
            pass

    # Unbounded default
    return TemporalContext(
        timeframe="all",
        start_date=None,
        end_date=None,
        timing=timing,
    )
