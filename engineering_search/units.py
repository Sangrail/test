"""Quantities: numbers with units, normalised to SI. Shared by indexing (facts) and searching (answers).

Units are normalised, never the intent: 5 N/m² stays 5 Pa and is not read as
5 kN/m². A value is compared only with values of the same dimension.
"""
from __future__ import annotations

import re

# A sign belongs to a number only at the start of a token: "-2 kN" is negative,
# "B-104" and the range "1-2 kN" are not.
SIGNED = r"(?<![\w.])[-−]?\d+(?:[.,]\d+)?|\b\d+(?:[.,]\d+)?"

# Unit -> (dimension, factor to the SI unit). Pressure in Pa, line load in N/m,
# force in N, mass in kg, length in m.
UNITS = {
    "n/m²": ("pressure", 1.0), "n/m2": ("pressure", 1.0), "pa": ("pressure", 1.0),
    "kn/m²": ("pressure", 1e3), "kn/m2": ("pressure", 1e3), "kpa": ("pressure", 1e3),
    "mpa": ("pressure", 1e6), "gpa": ("pressure", 1e9), "psf": ("pressure", 47.880),
    "psi": ("pressure", 6894.76), "ksi": ("pressure", 6.89476e6),
    "kn/m": ("line load", 1e3),
    "n": ("force", 1.0), "kn": ("force", 1e3), "kip": ("force", 4448.22),
    "kg": ("mass", 1.0), "t": ("mass", 1e3), "tonne": ("mass", 1e3), "tonnes": ("mass", 1e3),
    "mm": ("length", 1e-3), "cm": ("length", 1e-2), "m": ("length", 1.0), "ft": ("length", 0.3048),
    "in": ("length", 0.0254),
}
SI_UNITS = {"pressure": "Pa", "line load": "N/m", "force": "N", "mass": "kg", "length": "m"}
UNIT_PATTERN = (r"N/m²|N/m2|kN/m²|kN/m2|kN/m|kPa|MPa|GPa|Pa|psf|psi|ksi|kip|kN|kg|"
                r"tonnes?|t|mm|cm|m|ft|in|N")
QUANTITY = re.compile(rf"({SIGNED})\s?({UNIT_PATTERN})(?![\w/])", re.IGNORECASE)
# A unit on its own, as in a column header "Allowable UDL (kN/m²)".
HEADER_UNIT = re.compile(rf"[(\[]\s*({UNIT_PATTERN})\s*[)\]]", re.IGNORECASE)
NUMBER = re.compile(rf"^\s*({SIGNED})\s*$")


def number(text: str) -> float:
    """'-2', '−2' or '3,5' as a float."""
    return float(text.replace("−", "-").replace(",", "."))


def to_si(value: float, unit: str) -> tuple[str, float] | None:
    """(dimension, value in the SI unit), or None for an unknown unit."""
    known = UNITS.get(unit.casefold())
    return (known[0], value * known[1]) if known else None
