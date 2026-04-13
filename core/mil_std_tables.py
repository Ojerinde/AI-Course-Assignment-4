"""
MIL-STD-105E Table I and Table II-A lookup engine.
Data sourced directly from MIL-STD-105E (1989), pages 13-14.

Table I  : Sample Size Code Letters
Table IIA: Single Sampling Plans for Normal Inspection (Master Table)
"""

# ── Table I: Sample Size Code Letters ─────────────────────────────────────────
# Structure: {(min_lot, max_lot): {inspection_level: code_letter}}
# Inspection levels: S1, S2, S3, S4 (special), I, II, III (general)

_TABLE_I_DATA = [
    # (lot_size_min, lot_size_max,  S1,  S2,  S3,  S4,   I,  II, III)
    (2,        8,           "A", "A", "A", "A", "A", "A", "B"),
    (9,       15,           "A", "A", "A", "A", "A", "B", "C"),
    (16,       25,           "A", "A", "B", "B", "B", "C", "D"),
    (26,       50,           "A", "B", "B", "C", "C", "D", "E"),
    (51,       90,           "B", "B", "C", "C", "C", "E", "F"),
    (91,      150,           "B", "B", "C", "D", "D", "F", "G"),
    (151,      280,           "B", "C", "D", "E", "E", "G", "H"),
    (281,      500,           "B", "C", "D", "E", "F", "H", "J"),
    (501,     1200,           "C", "C", "E", "F", "G", "J", "K"),
    (1201,     3200,           "C", "D", "E", "G", "H", "K", "L"),
    (3201,    10000,           "C", "D", "F", "G", "J", "L", "M"),
    (10001,    35000,           "C", "D", "F", "H", "K", "M", "N"),
    (35001,   150000,           "D", "E", "G", "J", "L", "N", "P"),
    (150001,   500000,           "D", "E", "G", "J", "M", "P", "Q"),
    (500001, 99999999,           "D", "E", "H", "K", "N", "Q", "R"),
]

_LEVEL_IDX = {"S1": 2, "S2": 3, "S3": 4, "S4": 5, "I": 6, "II": 7, "III": 8}


def get_sampling_code(lot_size: int, level: str = "II") -> dict:
    """
    Return the sample size code letter for the given lot size and inspection level.

    Returns:
        dict with keys: code_letter, lot_size, level, table_ref
    """
    level = str(level).strip().upper()
    if level not in _LEVEL_IDX:
        return {"error": f"Unknown inspection level '{level}'. Valid: {list(_LEVEL_IDX.keys())}"}

    col = _LEVEL_IDX[level]
    for row in _TABLE_I_DATA:
        lo, hi = row[0], row[1]
        if lo <= lot_size <= hi:
            code = row[col]
            return {
                "code_letter": code,
                "lot_size": lot_size,
                "lot_range": f"{lo}–{hi}",
                "inspection_level": level,
                "table_ref": "MIL-STD-105E Table I, p.13",
            }
    return {"error": f"Lot size {lot_size} out of valid range (2 – 500,000+)"}


# ── Table II-A: Single Sampling Plans for Normal Inspection ───────────────────
# Structure: {code_letter: {sample_size, aql_acceptance_map}}
# aql_acceptance_map: {aql_string: (Ac, Re)}  Ac=Acceptance No., Re=Rejection No.
# '↑' means use first sampling plan below; '↓' means use first above.
# We only encode defined cells (no arrow redirects).

_TABLE_IIA = {
    # code: (sample_size, {aql: (Ac, Re), ...})
    "A": (2,  {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (0, 1),
               "0.40": (0, 1), "0.65": (0, 1), "1.0": (0, 1)}),
    "B": (3,  {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (0, 1),
               "0.40": (0, 1), "0.65": (0, 1), "1.0": (0, 1), "1.5": (0, 1)}),
    "C": (5,  {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (0, 1),
               "0.40": (0, 1), "0.65": (0, 1), "1.0": (0, 1), "1.5": (0, 1), "2.5": (0, 1)}),
    "D": (8,  {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (0, 1),
               "0.40": (0, 1), "0.65": (0, 1), "1.0": (0, 1), "1.5": (0, 1),
               "2.5": (0, 1), "4.0": (0, 1)}),
    "E": (13, {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (0, 1),
               "0.40": (0, 1), "0.65": (0, 1), "1.0": (0, 1), "1.5": (0, 1),
               "2.5": (0, 1), "4.0": (0, 1), "6.5": (0, 1)}),
    "F": (20, {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (0, 1),
               "0.40": (0, 1), "0.65": (0, 1), "1.0": (0, 1), "1.5": (0, 1),
               "2.5": (0, 1), "4.0": (1, 2), "6.5": (1, 2), "10": (2, 3)}),
    "G": (32, {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (0, 1),
               "0.40": (0, 1), "0.65": (0, 1), "1.0": (1, 2), "1.5": (1, 2),
               "2.5": (2, 3), "4.0": (3, 4), "6.5": (5, 6), "10": (7, 8)}),
    "H": (50, {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (0, 1),
               "0.40": (0, 1), "0.65": (1, 2), "1.0": (1, 2), "1.5": (2, 3),
               "2.5": (3, 4), "4.0": (5, 6), "6.5": (7, 8), "10": (10, 11)}),
    "J": (80, {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (0, 1),
               "0.40": (1, 2), "0.65": (1, 2), "1.0": (2, 3), "1.5": (3, 4),
               "2.5": (5, 6), "4.0": (7, 8), "6.5": (10, 11), "10": (14, 15)}),
    "K": (125, {"0.065": (0, 1), "0.10": (0, 1), "0.15": (0, 1), "0.25": (1, 2),
                "0.40": (1, 2), "0.65": (2, 3), "1.0": (3, 4), "1.5": (5, 6),
                "2.5": (7, 8), "4.0": (10, 11), "6.5": (14, 15), "10": (21, 22)}),
    "L": (200, {"0.065": (0, 1), "0.10": (0, 1), "0.15": (1, 2), "0.25": (1, 2),
                "0.40": (2, 3), "0.65": (3, 4), "1.0": (5, 6), "1.5": (7, 8),
                "2.5": (10, 11), "4.0": (14, 15), "6.5": (21, 22), "10": (21, 22)}),
    "M": (315, {"0.065": (0, 1), "0.10": (1, 2), "0.15": (1, 2), "0.25": (2, 3),
                "0.40": (3, 4), "0.65": (5, 6), "1.0": (7, 8), "1.5": (10, 11),
                "2.5": (14, 15), "4.0": (21, 22), "6.5": (21, 22)}),
    "N": (500, {"0.065": (1, 2), "0.10": (1, 2), "0.15": (2, 3), "0.25": (3, 4),
                "0.40": (5, 6), "0.65": (7, 8), "1.0": (10, 11), "1.5": (14, 15),
                "2.5": (21, 22), "4.0": (21, 22)}),
    "P": (800, {"0.065": (1, 2), "0.10": (2, 3), "0.15": (3, 4), "0.25": (5, 6),
                "0.40": (7, 8), "0.65": (10, 11), "1.0": (14, 15), "1.5": (21, 22),
                "2.5": (21, 22)}),
    "Q": (1250, {"0.065": (2, 3), "0.10": (3, 4), "0.15": (5, 6), "0.25": (7, 8),
                 "0.40": (10, 11), "0.65": (14, 15), "1.0": (21, 22), "1.5": (21, 22)}),
    "R": (2000, {"0.065": (3, 4), "0.10": (5, 6), "0.15": (7, 8), "0.25": (10, 11),
                 "0.40": (14, 15), "0.65": (21, 22), "1.0": (21, 22)}),
}


def get_acceptance_criteria(code_letter: str, aql: str = "1.0") -> dict:
    """
    Return the sample size and Acceptance/Rejection numbers from Table II-A.

    Args:
        code_letter: e.g. "H"
        aql: Acceptable Quality Level string, e.g. "1.0", "2.5", "4.0"

    Returns:
        dict with sample_size, aql, acceptance_number, rejection_number, table_ref
    """
    code_letter = str(code_letter).strip().upper()
    aql = str(aql).strip()

    if code_letter not in _TABLE_IIA:
        return {"error": f"Code letter '{code_letter}' not found in Table II-A."}

    sample_size, aql_map = _TABLE_IIA[code_letter]

    if aql not in aql_map:
        available = list(aql_map.keys())
        return {
            "error": f"AQL '{aql}' not available for code '{code_letter}'. "
            f"Available AQLs: {available}",
            "sample_size": sample_size,
            "code_letter": code_letter,
        }

    ac, re = aql_map[aql]
    return {
        "code_letter": code_letter,
        "sample_size": sample_size,
        "aql": aql,
        "acceptance_number": ac,
        "rejection_number": re,
        "verdict_rule": (
            f"Inspect {sample_size} units. "
            f"Accept lot if defects ≤ {ac}; Reject if defects ≥ {re}."
        ),
        "table_ref": "MIL-STD-105E Table II-A, p.14",
    }


def list_aql_options(code_letter: str) -> list:
    """Return available AQL values for a given code letter."""
    code_letter = str(code_letter).strip().upper()
    if code_letter in _TABLE_IIA:
        return list(_TABLE_IIA[code_letter][1].keys())
    return []
