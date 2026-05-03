from pathlib import Path
import os
import sys


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

DEFAULT_SETTINGS = {
    "app_mode": "",
    "default_class_id": None,
    "default_subject_id": None,
    "primary_class_id": None,
    "school_name": "",
    "teacher_name": "",
    "academic_year": "",
    "semester": "Ganjil",
    "kkm": 75,
    "weight_task": 30,
    "weight_mid": 30,
    "weight_final": 40,
    "daily_component_count": 3,
    "use_daily_components": 1,
    "use_mid_component": 1,
    "use_final_component": 1,
}
