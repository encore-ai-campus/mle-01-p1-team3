from __future__ import annotations

from typing import Any


def format_value(value: Any) -> str:
    if value is None or value == "":
        return "정보 없음"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return f"{int(stripped):,}"
        return stripped or "정보 없음"
    return str(value)


def get_active_ability_options(ability: dict[str, Any]) -> list[str]:
    preset_no = ability.get("preset_no")
    preset = ability.get(f"ability_preset_{preset_no}") if preset_no else None
    if not isinstance(preset, dict) and preset_no:
        preset = ability.get(f"ability_preset{preset_no}")
    if not isinstance(preset, dict):
        preset = ability

    options = preset.get("ability_info", [])
    if not isinstance(options, list):
        return []

    return [
        str(item.get("ability_value"))
        for item in options
        if isinstance(item, dict) and item.get("ability_value")
    ]


def get_hyper_stat_rows(hyper_stat: dict[str, Any]) -> list[tuple[str, Any]]:
    preset_no = hyper_stat.get("use_preset_no") or "1"
    rows = hyper_stat.get(f"hyper_stat_preset_{preset_no}", [])
    if not isinstance(rows, list):
        rows = hyper_stat.get(f"hyper_stat_preset{preset_no}", [])
    if not isinstance(rows, list):
        return []
    return [
        (str(item.get("stat_type", "스탯")), item.get("stat_level"))
        for item in rows
        if isinstance(item, dict)
    ]
