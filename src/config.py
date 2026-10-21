import json
import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    db_host: str = "192.168.31.121"
    db_port: int = 5432
    db_name: str = "notes"
    db_user: str = "notes"
    db_password: str = "notes_dev_pass"


def _settings_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        folder = Path(appdata) / "NotesApp"
    else:
        folder = Path.home() / ".notes_app"
    return folder / "settings.json"


def load_settings() -> Settings:
    path = _settings_path()
    if not path.exists():
        s = Settings()
        save_settings(s)
        return s
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Settings(**data)
    except Exception:
        s = Settings()
        save_settings(s)
        return s


def save_settings(s: Settings) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(s.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
