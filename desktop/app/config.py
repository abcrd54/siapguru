from pathlib import Path
import os
import sys


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _load_env_candidates() -> None:
    candidates: list[Path] = []
    project_root = Path(__file__).resolve().parent.parent
    candidates.append(project_root / ".env")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / ".env")
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(Path(meipass) / ".env")
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        _load_env_file(candidate)


_load_env_candidates()


APP_NAME = "SiapGuru"
LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
USER_PROFILE = Path(os.environ.get("USERPROFILE", Path.home()))
DOCUMENTS_DIR = Path(os.environ.get("SIAPGURU_DOCUMENTS_DIR", USER_PROFILE / "Documents"))
APP_DIR = LOCAL_APPDATA / APP_NAME
WORKSPACES_DIR = APP_DIR / "workspaces"
APP_STATE_PATH = APP_DIR / "app_state.json"
LICENSE_SOURCE = os.environ.get("SIAPGURU_LICENSE_SOURCE", "firebase")
LOCAL_LICENSE_PATH = APP_DIR / "license_local.json"
LOCAL_LICENSE_KEYS_PATH = APP_DIR / "license_keys_local.json"
FIREBASE_LICENSE_CACHE_PATH = APP_DIR / "license_firebase_cache.json"
FIREBASE_UPDATE_CACHE_PATH = APP_DIR / "update_firebase_cache.json"
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    "SIAPGURU_FIREBASE_CREDENTIALS",
    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
)
FIREBASE_PROJECT_ID = os.environ.get("SIAPGURU_FIREBASE_PROJECT_ID", "")
FIREBASE_COLLECTION = os.environ.get("SIAPGURU_FIREBASE_COLLECTION", "licenses")
FIREBASE_RELEASES_COLLECTION = os.environ.get("SIAPGURU_FIREBASE_RELEASES_COLLECTION", "app_releases")
FIREBASE_RELEASE_CHANNEL = os.environ.get("SIAPGURU_FIREBASE_RELEASE_CHANNEL", "production")
APP_VERSION = os.environ.get("SIAPGURU_APP_VERSION", "1.0.0")
DB_PATH = APP_DIR / "siapguru.db"
EXPORT_DIR = DOCUMENTS_DIR / APP_NAME
BACKUP_DIR = DOCUMENTS_DIR / APP_NAME / "backup"
MODULES_DIR_NAME = "modules"
ADMIN_LICENSE_CACHE_PATH = APP_DIR / "license_admin_cache.json"
ADMIN_API_BASE_URL = os.environ.get("SIAPGURU_ADMIN_API_BASE_URL", "").strip()
ADMIN_API_TOKEN = os.environ.get("SIAPGURU_ADMIN_API_TOKEN", "").strip()
ADMIN_API_TIMEOUT = int(os.environ.get("SIAPGURU_ADMIN_API_TIMEOUT", "120") or "120")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "inclusionai/ling-2.6-1t:free").strip()
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "").strip()
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "").strip()
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "").strip()

DEFAULT_SETTINGS = {
    "app_mode": "",
    "default_class_id": None,
    "default_subject_id": None,
    "primary_class_id": None,
    "school_name": "",
    "teacher_name": "",
    "academic_year": "",
    "semester": "Ganjil",
    "admin_api_base_url": ADMIN_API_BASE_URL,
    "admin_api_token": ADMIN_API_TOKEN,
    "kkm": 75,
    "weight_task": 30,
    "weight_mid": 30,
    "weight_final": 40,
    "daily_component_count": 3,
    "use_daily_components": 1,
    "use_mid_component": 1,
    "use_final_component": 1,
}
