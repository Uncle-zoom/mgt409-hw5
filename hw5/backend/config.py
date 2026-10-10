"""Settings for the agent team: model, limits and paths, in one place."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
MCP_SERVER_PATH = ROOT / "mcp_server" / "server.py"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
REQUIRED_MODEL = "gpt-6-luna"

AGENT_NAMES = ("boss", "inventory", "accounting", "facilities", "customer_service")


@dataclass(frozen=True)
class Limits:
    """Hard limits, enforced in code (see team.py)."""

    request_limit_per_agent_run: int = 8
    total_tokens_per_ticket: int = 100_000
    model_call_timeout_seconds: float = 60.0
    max_delegation_depth: int = 3


LIMITS = Limits()


class ConfigError(RuntimeError):
    """Raised when the environment is not set up to run the agents."""


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str


def load_settings() -> Settings:
    """Read .env and refuse to continue unless MODEL is exactly gpt-6-luna."""
    load_dotenv(ROOT / ".env")
    model = os.getenv("MODEL", "").strip()
    if model != REQUIRED_MODEL:
        raise ConfigError(
            f"MODEL must be '{REQUIRED_MODEL}' in .env (found {model!r}). Refusing to start."
        )
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key or api_key == "your-key-here":
        raise ConfigError("PORTKEY_API_KEY is missing from .env. Refusing to start.")
    return Settings(api_key=api_key, model=model)
