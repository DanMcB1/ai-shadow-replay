"""Paths and defaults. Optional LLM hook is off unless an env var is set."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPANY = "Lakeside Auto Group (sample)"
TICKET_COUNT = 200
TICKET_SEED = 10

# Go / no-go defaults. These are demo thresholds, not a customer's policy.
GATE_POLICY_PASS_MIN = 0.90
GATE_MAX_CRITICAL = 0

STORES = [
    "Harbor CDJR",
    "Westbrook Chevrolet",
    "Lakeside Honda",
    "Northlake Toyota",
    "Parkside Ford",
    "Summit Kia",
]


def data_dir() -> Path:
    path = Path(os.environ.get("SHADOW_REPLAY_DATA", ROOT / "data"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def tickets_path() -> Path:
    return Path(os.environ.get("SHADOW_REPLAY_TICKETS", data_dir() / "tickets.json"))


def db_path() -> Path:
    return Path(os.environ.get("SHADOW_REPLAY_DB", data_dir() / "replay.sqlite"))


def llm_base_url() -> str:
    return os.environ.get("SHADOW_REPLAY_LLM_BASE_URL", "").strip()


def llm_api_key() -> str:
    return os.environ.get("SHADOW_REPLAY_LLM_API_KEY", "").strip()


def llm_model() -> str:
    return os.environ.get("SHADOW_REPLAY_LLM_MODEL", "shadow-replay-mock")


def llm_is_external() -> bool:
    return bool(llm_base_url())
