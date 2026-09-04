"""Loads download_ig_prices.ipynb's credentials and settings from `.env`
(see .env.sample) into a single Config object, so notebook cells pass around
`cfg.epic` etc. instead of repeating `os.environ.get(...)` + parsing."""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from constants.csv_filename_suffix import RESOLUTION_CSV_SUFFIX
from constants.env_keys import EnvKey


def _env_bool(value):
    return value.strip().lower() == "true"


def _epic_slug(epic):
    """Derive a filename-safe slug from an IG epic, e.g.
    "IX.D.NASDAQ.IFA.IP" -> "nasdaq" (the instrument segment, lowercased);
    falls back to the whole epic, lowercased, if it isn't dot-segmented."""

    parts = epic.split(".")
    return (parts[2] if len(parts) >= 3 else epic).lower()


@dataclass(frozen=True)
class Config:
    env_path: Path

    api_key: str
    username: str
    password: str
    account_type: str

    epic: str
    resolution: str
    days_back: int
    save_csv: bool
    save_db: bool

    data_dir: Path
    csv_path: Path
    db_path: Path

    @classmethod
    def from_env(cls, env_path=Path(".env")):
        """Load `env_path` (git-ignored) and build a Config from it. Raises
        FileNotFoundError if it doesn't exist, KeyError if a required IG
        credential is missing."""

        if not env_path.exists():
            raise FileNotFoundError(
                f"{env_path.resolve()} not found - create it with IG_API_KEY / "
                "IG_USERNAME / IG_PASSWORD / IG_ACCOUNT_TYPE"
            )
        load_dotenv(env_path, override=True)

        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        run_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        epic = os.environ.get(EnvKey.IG_EPIC, "IX.D.NASDAQ.IFA.IP")
        resolution = os.environ.get(EnvKey.IG_RESOLUTION, "DAY")

        return cls(
            env_path=env_path,
            api_key=os.environ[EnvKey.IG_API_KEY],
            username=os.environ[EnvKey.IG_USERNAME],
            password=os.environ[EnvKey.IG_PASSWORD],
            account_type=os.environ.get(EnvKey.IG_ACCOUNT_TYPE, "demo").lower(),
            epic=epic,
            resolution=resolution,
            days_back=int(os.environ.get(EnvKey.IG_DAYS_BACK, "1")),
            save_csv=_env_bool(os.environ.get(EnvKey.IG_SAVE_CSV, "true")),
            save_db=_env_bool(os.environ.get(EnvKey.IG_SAVE_DB, "false")),
            data_dir=data_dir,
            csv_path=data_dir / (
                f"ig_{_epic_slug(epic)}_"
                f"{RESOLUTION_CSV_SUFFIX.get(resolution, resolution.lower())}_"
                f"{run_timestamp}.csv"
            ),
            db_path=data_dir / "ig_market_data.db",
        )
