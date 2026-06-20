import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "management_table.sqlite3"
DATABASE_URL = (
    os.environ.get("DATABASE_URL", "")
    or os.environ.get("POSTGRES_URL", "")
    or os.environ.get("POSTGRES_PRISMA_URL", "")
    or os.environ.get("POSTGRES_URL_NON_POOLING", "")
).strip()

STATE_KEY = "product_distribution"
REELFARM_API_KEY = "reel_farm_api_key"
PUBLISH_CHECK_STATE_KEY = "publish_check_state"
EXTERNAL_API_KEYS_KEY = "external_api_keys"
SEED_DATA_PATH = BASE_DIR / "seed_data.json"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Deca888").strip()
ADMIN_PASSWORD_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    "baacd133a9696faa0333b9a7a8d3f0e3b560ef781a494d017d0d2ea19d46c0b1",
).strip()
SESSION_SECRET = os.environ.get("SESSION_SECRET", ADMIN_PASSWORD_HASH).strip()
SESSION_COOKIE = "deca_growth_session"
SESSION_TTL_SECONDS = 60 * 60 * 12
CRON_SECRET = os.environ.get("CRON_SECRET", "").strip()

AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
REELFARM_BASE_URL = "https://reel.farm/api/v1"
MUSEON_BASE_URL = os.environ.get("MUSEON_BASE_URL", "https://api.museon.ai/external/api/v1").strip().rstrip("/")
MUSEON_API_KEY = os.environ.get("MUSEON_API_KEY", "").strip()
MUSEON_WORKSPACE_ID = os.environ.get("MUSEON_WORKSPACE_ID", "b5e25f84-b3ed-484b-b467-901a4afcd9c6").strip()
MUSEON_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
MIXPANEL_REGION = os.environ.get("MIXPANEL_REGION", "standard").strip().lower()
REPORT_TIMEZONE_NAME = os.environ.get("REPORT_TIMEZONE", "Asia/Shanghai").strip()
MIXPANEL_TIMEZONE_NAME = os.environ.get("MIXPANEL_TIMEZONE", "America/Los_Angeles").strip()
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
FEISHU_WEBHOOK_SECRET = os.environ.get("FEISHU_WEBHOOK_SECRET", "").strip()
LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1").strip().rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4.1-mini").strip()
FALLBACK_LLM_MODELS = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
]
