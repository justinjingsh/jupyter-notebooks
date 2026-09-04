"""Names of the environment variables loaded from `.env` (see .env.sample)."""


class EnvKey:
    """Environment variable names read via `os.environ` after `load_dotenv()`."""
    IG_API_KEY = "IG_API_KEY"
    IG_USERNAME = "IG_USERNAME"
    IG_PASSWORD = "IG_PASSWORD"
    IG_ACCOUNT_TYPE = "IG_ACCOUNT_TYPE"
    IG_EPIC = "IG_EPIC"
    IG_RESOLUTION = "IG_RESOLUTION"
    IG_DAYS_BACK = "IG_DAYS_BACK"
    IG_SAVE_CSV = "IG_SAVE_CSV"
    IG_SAVE_DB = "IG_SAVE_DB"
