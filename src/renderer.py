"""Simple rendering helpers for human-friendly output.

Includes utilities to pull dotted paths out of dicts and render labeled
sections or basic markdown tables based on `FieldSpec` definitions.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass
class FieldSpec:
    label: str
    path: str  # dotted path into data
    icon: str = ""
    transform: Callable[[Any, dict], str | None] | None = None


def get_path(data: dict, path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def render_fields(specs: Sequence[FieldSpec], data: dict) -> list[str]:
    lines: list[str] = []
    for spec in specs:
        raw = get_path(data, spec.path)
        val = spec.transform(raw, data) if spec.transform else raw
        if val in (None, "", []):
            continue
        icon = f"{spec.icon} " if spec.icon else ""
        lines.append(f"{icon}{spec.label}: {val}")
    return lines


def render_section(title: str | None, specs: Sequence[FieldSpec], data: dict) -> str:
    body = "\n".join(render_fields(specs, data)).rstrip()
    if not body:
        return ""
    return f"{title}\n{body}\n" if title else f"{body}\n"


def render_table(specs: Sequence[FieldSpec], data: dict) -> str:
    rows: list[tuple[str, str]] = []
    for spec in specs:
        raw = get_path(data, spec.path)
        val = spec.transform(raw, data) if spec.transform else raw
        if val in (None, "", []):
            continue
        label = f"{spec.icon} {spec.label}".strip()
        # Escape pipe characters in values to avoid breaking markdown tables
        val_str = str(val).replace("|", "\\|")
        rows.append((label, val_str))
    if not rows:
        return ""
    out = ["| Field | Value |", "|---|---|"]
    out += [f"| {label} | {val} |" for label, val in rows]
    return "\n".join(out) + "\n"
