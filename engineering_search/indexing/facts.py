"""Facts: typed values from table rows, extracted at index time by fixed rules.

Each fact is one cell, with what the row is about (subject), what the value is
(parameter and role), the value as written, and the value in SI units. The rules
read the column header, the table name and the cell; they never guess from free
text. A cell that the rules cannot classify but that holds a quantity becomes a
fact with the column name as its parameter and the role "unknown".

Controlled parameters (extend after evaluation):
    material_grade              S355J2+N, C30/37, B500B, Grade 50
    allowable_distributed_load  a capacity, as a pressure (kN/m²)
    load_capacity               a capacity, as a force (kN)
    roof_imposed_load           a demand on a roof, as a pressure
    imposed_load                another demand, as a pressure
    applied_load                a demand, as a force
    settlement, deflection      measurements, as a length (signed)
    compliance_status           approved, rejected, pending, ... as written

In a key-value table ("| Parameter | Value | Approval status |"), the row label
takes the place of the column header, and the subject is the table's heading.

Capacity and demand are never the same parameter: a query for allowable loads
does not see imposed loads.
"""
from __future__ import annotations

import re

from ..core import Fact, Table
from ..units import HEADER_UNIT, NUMBER, QUANTITY, number, to_si

SUBJECT_HEADER = re.compile(r"\b(component|member|element|mark|item|ref|reference|id|tag|beam|name|location)\b", re.I)
PROJECT_HEADER = re.compile(r"\bproject\b", re.I)
GRADE_HEADER = re.compile(r"\b(grade|material|steel|concrete)\b", re.I)
STATUS_HEADER = re.compile(r"\b(status|approval|compliance)\b", re.I)
GRADE = re.compile(r"^\s*(S\d{3}[A-Z0-9+]*|C\d{2}/\d{2}|B500[A-C]|Grade\s+(?:HPS\s+)?\d+W?)\s*$", re.I)
CAPACITY = re.compile(r"\b(allowable|capacity|resistance|udl|permissible|safe working|maximum|limit)\b", re.I)
DEMAND = re.compile(r"\b(imposed|applied|design load|live|actual|demand)\b", re.I)
SETTLEMENT = re.compile(r"\bsettlement\b", re.I)
DEFLECTION = re.compile(r"\bdeflection\b", re.I)
# A key-value table: "| Parameter | Value | ... |", one parameter per row.
KEY_HEADER = re.compile(r"^(parameter|property|item|description|quantity)$", re.I)
VALUE_HEADER = re.compile(r"^value$", re.I)
EMPTY = {"", "-", "—", "–", "n/a", "na", "none", "tbc", "tbd"}


def slug(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", HEADER_UNIT.sub("", header).casefold()).strip("_") or "value"


def classify(header: str, table_name: str, dimension: str) -> tuple[str, str]:
    """(parameter, role) of a quantity in a column."""
    if dimension == "pressure":
        if CAPACITY.search(header):
            return "allowable_distributed_load", "capacity"
        if DEMAND.search(header):
            roof = re.search(r"\broof\b", f"{header} {table_name}", re.I)
            return ("roof_imposed_load" if roof else "imposed_load"), "demand"
    if dimension == "force":
        if CAPACITY.search(header):
            return "load_capacity", "capacity"
        if DEMAND.search(header):
            return "applied_load", "demand"
    if dimension == "length":
        if SETTLEMENT.search(header):
            return "settlement", "measurement"
        if DEFLECTION.search(header):
            return "deflection", "measurement"
    return slug(header), "unknown"


def quantity(cell: str, header: str) -> tuple[float, str] | None:
    """(number, unit) from the cell, or from a plain number and the unit in the header."""
    if match := QUANTITY.fullmatch(cell.strip()):
        return number(match.group(1)), match.group(2)
    header_unit = HEADER_UNIT.search(header)
    if header_unit and (match := NUMBER.match(cell)):
        return number(match.group(1)), header_unit.group(1)
    return None


def cell_fact(header: str, cell: str, table_name: str, base: dict) -> Fact | None:
    """The fact in one cell, or None if the rules do not apply."""
    if GRADE_HEADER.search(header) and GRADE.match(cell):
        return Fact(parameter="material_grade", role="specification", **base)
    if STATUS_HEADER.search(header):
        return Fact(parameter="compliance_status", role="status", **base)
    if found := quantity(cell, header):
        value, unit = found
        si = to_si(value, unit)
        if si is not None:
            parameter, role = classify(header, table_name, si[0])
            return Fact(parameter=parameter, role=role, number=value, unit=unit,
                        si_value=si[1], dimension=si[0], **base)
    return None


def key_value_facts(table: Table, value_column: int) -> list[Fact]:
    facts = []
    for row in table.rows:
        label = row.cells[0]
        for i, (header, cell) in enumerate(zip(table.columns, row.cells)):
            if i == 0 or cell.strip().casefold() in EMPTY:
                continue
            base = dict(table=table.table, row=row.row, column=header, subject=table.name, value=cell)
            fact = cell_fact(label if i == value_column else header, cell, table.name, base)
            if fact is not None:
                facts.append(fact)
    return facts


def extract_facts(tables: tuple[Table, ...]) -> tuple[Fact, ...]:
    facts = []
    for table in tables:
        columns = table.columns
        value_column = next((i for i, c in enumerate(columns) if VALUE_HEADER.match(c)), None)
        if columns and KEY_HEADER.match(columns[0]) and value_column is not None:
            facts += key_value_facts(table, value_column)
            continue
        subject_column = next((i for i, c in enumerate(columns) if SUBJECT_HEADER.search(c)), 0)
        project_column = next((i for i, c in enumerate(columns) if PROJECT_HEADER.search(c)), None)
        if project_column == subject_column:
            subject_column = next((i for i in range(len(columns)) if i != project_column), subject_column)
        for row in table.rows:
            subject = row.cells[subject_column] if subject_column < len(row.cells) else ""
            project = row.cells[project_column] if project_column is not None else None
            for i, (header, cell) in enumerate(zip(columns, row.cells)):
                if i in (subject_column, project_column) or cell.strip().casefold() in EMPTY:
                    continue
                base = dict(table=table.table, row=row.row, column=header, subject=subject, value=cell,
                            project=project or None)
                fact = cell_fact(header, cell, table.name, base)
                if fact is not None:
                    facts.append(fact)
    return tuple(facts)
