import json
import os
from datetime import datetime, timedelta
import pandas as pd
from modules.data_manager import data_manager


def _safe_parse_iso_date(text):
    if not text:
        return None
    try:
        return datetime.fromisoformat(str(text)[:10]).date()
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        return None


def load_universe_flags(path_str):
    path = Path(path_str)
    if not path.exists():
        return {"version": 1, "updated_at": None, "symbols": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e: 
        import logging
        logging.error(f"Error: {e}", exc_info=True)
        return {"version": 1, "updated_at": None, "symbols": {}}
    if not isinstance(payload, dict):
        return {"version": 1, "updated_at": None, "symbols": {}}
    payload.setdefault("version", 1)
    payload.setdefault("updated_at", None)
    if not isinstance(payload.get("symbols"), dict):
        payload["symbols"] = {}
    return payload


def save_universe_flags(path_str, payload):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def refresh_and_get_blocked_symbols(payload, as_of):
    symbols = payload.setdefault("symbols", {})
    blocked = set()
    today_iso = as_of.isoformat()
    for sym, rec in symbols.items():
        if not isinstance(rec, dict):
            continue
        status = str(rec.get("status", "active")).lower()
        if status != "inactive":
            continue
        expires_on = _safe_parse_iso_date(rec.get("expires_on"))
        if expires_on is not None and expires_on < as_of:
            rec["status"] = "active"
            rec["reactivated_on"] = today_iso
            rec["consecutive_failures"] = 0
            continue
        blocked.add(sym.upper())
    return blocked


def update_universe_flags(
    payload,
    failed_reason_by_symbol,
    successful_symbols,
    as_of,
    *,
    failure_threshold,
    cooldown_days,
    min_success_ratio,
    max_new_inactive,
    whitelist,
    reason_thresholds=None,
):
    symbols = payload.setdefault("symbols", {})
    day_iso = as_of.isoformat()
    reason_map = {}
    for sym, reason in (failed_reason_by_symbol or {}).items():
        if not sym:
            continue
        key = str(sym).upper()
        reason_map[key] = str(reason or "fetch_failed")
    failed = set(reason_map.keys())
    successful = {str(s).upper() for s in successful_symbols if s}
    wl = {str(s).upper() for s in whitelist if s}
    reason_thresholds = reason_thresholds or {}

    attempted = len(failed | successful)
    success_ratio = (len(successful) / attempted) if attempted else 0.0

    for sym in successful:
        rec = symbols.setdefault(sym, {})
        rec["last_success_date"] = day_iso
        rec["consecutive_failures"] = 0
        if str(rec.get("status", "active")).lower() == "inactive":
            rec["status"] = "active"
            rec["reactivated_on"] = day_iso

    new_inactive = 0
    if attempted and success_ratio >= min_success_ratio:
        for sym in sorted(failed - wl):
            rec = symbols.setdefault(sym, {})
            reason = reason_map.get(sym, "fetch_failed")
            prev = int(rec.get("consecutive_failures", 0) or 0)
            reason_failures = rec.setdefault("reason_failures", {})
            prev_reason_hits = int(reason_failures.get(reason, 0) or 0)
            # Increment at most once per run/day.
            if rec.get("last_failure_date") != day_iso or rec.get("last_failure_reason") != reason:
                rec["consecutive_failures"] = prev + 1
                rec["total_failures"] = int(rec.get("total_failures", 0) or 0) + 1
                reason_failures[reason] = prev_reason_hits + 1
            rec["last_failure_date"] = day_iso
            rec["last_failure_reason"] = reason

            required = int(reason_thresholds.get(reason, failure_threshold))
            if (
                int(reason_failures.get(reason, 0) or 0) >= required
                and str(rec.get("status", "active")).lower() != "inactive"
                and new_inactive < int(max_new_inactive)
            ):
                rec["status"] = "inactive"
                rec["reason"] = reason
                rec["inactive_since"] = day_iso
                rec["expires_on"] = (as_of + timedelta(days=int(cooldown_days))).isoformat()
                new_inactive += 1

    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    blocked = refresh_and_get_blocked_symbols(payload, as_of)
    return {
        "attempted": attempted,
        "successful": len(successful),
        "failed": len(failed),
        "success_ratio": round(success_ratio, 4),
        "new_inactive": new_inactive,
        "blocked_total": len(blocked),
        "guarded_by_outage": attempted > 0 and success_ratio < min_success_ratio,
    }
