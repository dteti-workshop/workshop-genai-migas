"""Modul extraction work order yang dipakai oleh app_asisten_wo.py (Unit 8).

Schema dan fungsi extract_one sama dengan Unit 4. Prompt terbaik dari Unit 4 ditempel pada SYSTEM_EXTRACT.
"""
from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, ValidationError, field_validator

from common.llm import chat, parse_json

EquipmentType = Literal["ESP", "SRP", "PCP", "Steam Generator", "Flowline", "Separator",
                        "Gas Compressor", "Water Injection Pump"]
FailureCategory = Literal["Electrical", "Mechanical", "Leak/Corrosion", "Flow Assurance",
                          "Instrumentation/Control", "Process/Trip", "Preventive Maintenance"]
ActionCategory = Literal["Replace", "Repair", "Clean/Flush", "Adjust/Reset", "Workover"]


class WOExtract(BaseModel):
    asset_id: str
    equipment_type: EquipmentType
    failure_category: FailureCategory
    component: str
    action_category: ActionCategory
    downtime_hours: float = Field(ge=0, le=24 * 30)
    safety_flag: bool

    @field_validator("asset_id")
    @classmethod
    def kapital(cls, v: str) -> str:
        return v.strip().upper()


# TODO(U8.1): tempel prompt extraction terbaik dari Unit 4 (SYSTEM_V1 + TAMBAHAN_V2)
SYSTEM_EXTRACT = "Ekstrak data work order ke JSON."  # TODO: ganti dengan implementasi Anda


def extract_one(desc: str, max_repair: int = 2) -> dict:
    """Extraction satu work order dengan validasi schema dan self-repair."""
    messages = [{"role": "user", "content": f"<wo>{desc}</wo>"}]
    for _ in range(max_repair + 1):
        raw = chat(messages, system=SYSTEM_EXTRACT, json_mode=True)
        try:
            return WOExtract.model_validate(parse_json(raw)).model_dump()
        except (ValidationError, ValueError) as e:
            messages += [{"role": "assistant", "content": raw},
                         {"role": "user", "content": f"Output tidak valid terhadap schema:\n{e}\n"
                                                     "Perbaiki dan kembalikan JSON saja."}]
    raise ValueError("Extraction gagal")


def max_failures_in_window(dates: pd.Series, days: int = 90) -> int:
    """Jumlah kegagalan terbanyak dalam satu jendela waktu sepanjang `days` hari."""
    d = dates.sort_values().reset_index(drop=True)
    return max((d.searchsorted(d[i] + pd.Timedelta(days=days), side="right") - i for i in range(len(d))), default=0)
