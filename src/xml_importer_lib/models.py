from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ImportStats:
    single_projects: int = 0
    single_project_profiles: int = 0
    single_project_extras: int = 0
    unit_projects: int = 0
    unit_project_extras: int = 0
    divisions: int = 0
    boq_items: int = 0
    quotas: int = 0
    resource_summaries: int = 0
    resource_usages: int = 0
    elapsed_seconds: float = 0.0


SINGLE_PROJECT_PROFILE_FIELDS = (
    "工程类型",
    "结构类型",
    "基础类型",
    "主要工程特征",
    "层数",
    "檐高",
)
