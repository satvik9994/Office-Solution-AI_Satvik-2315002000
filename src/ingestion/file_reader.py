"""Robust file ingestion and sanitization for Tableau and DAX artifacts."""

import io
import json
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import pandas as pd

from ingestion.models import (
    CalculationItem,
    VisualItem,
    IncorrectDaxItem,
    GroundTruthItem,
)


def clean_file_content(file_path: str) -> str:
    """Reads file handling UTF-8 BOM and stripping CSV-style line wrapping quotes."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8-sig") as f:
        text = f.read()

    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        l = line.rstrip()
        if l.startswith('"') and l.endswith('"'):
            l = l[1:-1].replace('""', '"')
        cleaned_lines.append(l)

    return os.linesep.join(cleaned_lines)


def load_calculations(file_path: str) -> List[CalculationItem]:
    """Loads calculation definitions from a JSON file."""
    content = clean_file_content(file_path)
    data = json.loads(content)
    items = []
    for item in data:
        items.append(
            CalculationItem(
                id=item["id"],
                name=item["name"],
                formula=item["formula"],
                source_type="json_calc",
                raw_metadata=item,
            )
        )
    return items


def load_dependencies(file_path: str) -> List[CalculationItem]:
    """Loads dependent calculation definitions, synthesizing IDs if missing."""
    content = clean_file_content(file_path)
    data = json.loads(content)
    items = []
    for idx, item in enumerate(data, start=1):
        calc_id = item.get("id", f"dep_{item['name']}")
        items.append(
            CalculationItem(
                id=calc_id,
                name=item["name"],
                formula=item["formula"],
                source_type="json_dep",
                raw_metadata=item,
            )
        )
    return items


def load_tableau_xml(file_path: str) -> List[CalculationItem]:
    """Loads calculations defined inside Tableau XML workbook format."""
    content = clean_file_content(file_path)
    root = ET.fromstring(content)
    items = []
    for calc_elem in root.findall(".//calculation"):
        name = calc_elem.get("name")
        formula = calc_elem.get("formula")
        if not formula:
            continue
        calc_id = f"xml_{name}" if name else f"xml_calc_{len(items)+1}"
        calc_name = name if name else calc_id
        items.append(
            CalculationItem(
                id=calc_id,
                name=calc_name,
                formula=formula,
                source_type="xml_calc",
                raw_metadata=dict(calc_elem.attrib),
            )
        )
    return items


def load_incorrect_dax(file_path: str) -> Dict[str, IncorrectDaxItem]:
    """Loads flawed legacy DAX conversions into an ID-indexed lookup dictionary."""
    content = clean_file_content(file_path)
    data = json.loads(content)
    result = {}
    for item in data:
        result[item["id"]] = IncorrectDaxItem(
            id=item["id"],
            dax=item["dax"],
        )
    return result


def load_ground_truth(file_path: str) -> Dict[str, GroundTruthItem]:
    """Loads ground-truth target DAX into an ID-indexed lookup dictionary."""
    content = clean_file_content(file_path)
    data = json.loads(content)
    result = {}
    for item in data:
        result[item["id"]] = GroundTruthItem(
            id=item["id"],
            dax=item["dax"],
        )
    return result


def load_visuals(file_path: str) -> List[VisualItem]:
    """Loads visual configurations from visuals.json."""
    content = clean_file_content(file_path)
    data = json.loads(content)
    items = []
    for item in data:
        items.append(
            VisualItem(
                id=item["id"],
                tableau_visual=item["tableau_visual"],
                dimensions=item.get("dimensions", []),
                measures=item.get("measures", []),
                expected_powerbi=item.get("expected_powerbi"),
            )
        )
    return items


def load_sample_data(file_path: str) -> pd.DataFrame:
    """Loads sample data from CSV or Excel, correcting for single-cell line wrapping."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Sample data file not found: {file_path}")

    if file_path.endswith(".csv"):
        cleaned_content = clean_file_content(file_path)
        df = pd.read_csv(io.StringIO(cleaned_content))
    elif file_path.endswith((".xlsx", ".xls")):
        df_raw = pd.read_excel(file_path)
        if len(df_raw.columns) == 1 and "," in str(df_raw.columns[0]):
            header = [col.strip() for col in df_raw.columns[0].split(",")]
            rows = [str(val).split(",") for val in df_raw.iloc[:, 0]]
            df = pd.DataFrame(rows, columns=header)
            for col in ["Sales", "Profit", "Cost"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df = df_raw
    else:
        raise ValueError(f"Unsupported tabular data format: {file_path}")

    return df