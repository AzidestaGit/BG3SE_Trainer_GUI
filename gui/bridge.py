"""
File-based bridge to the in-game BG3GuiBridge Lua mod.

The Lua mod writes/reads everything through Ext.IO relative to BG3SE's sandboxed
storage root. That root is a real directory on disk (Proton doesn't virtualize the
filesystem), so this module just needs to find it once and then does plain file I/O.
"""
import json
import time
import uuid
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"
PROBE_NAME = "probe.txt"
BRIDGE_FOLDER_NAME = "BG3GuiBridge"

# Known/likely places a BG3SE Lua sandbox root could live, based on this machine's
# Steam layout (adjust SEARCH_ROOTS if your library is elsewhere).
SEARCH_ROOTS = [
    Path.home() / ".local/share/Steam/steamapps/compatdata",
    Path("/mnt/games/SteamLibrary/steamapps/compatdata"),
]


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def find_bridge_dir(max_depth: int = 10) -> Path | None:
    """Search known Proton prefixes for the probe file the Lua mod writes on load."""
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for prefix in root.glob("*/pfx/drive_c/users/*/AppData"):
            for match in prefix.rglob(PROBE_NAME):
                if match.parent.name == BRIDGE_FOLDER_NAME:
                    return match.parent
    return None


class Bridge:
    def __init__(self):
        cfg = _load_config()
        stored = cfg.get("bridge_dir")
        self.bridge_dir: Path | None = Path(stored) if stored else None

    def is_configured(self) -> bool:
        return self.bridge_dir is not None and self.bridge_dir.exists()

    def autodetect(self) -> bool:
        found = find_bridge_dir()
        if found:
            self.set_bridge_dir(found)
            return True
        return False

    def set_bridge_dir(self, path: Path) -> None:
        self.bridge_dir = path
        _save_config({"bridge_dir": str(path)})

    def _path(self, name: str) -> Path:
        assert self.bridge_dir is not None
        return self.bridge_dir / name

    def send_action(self, action: str, params: dict | None = None) -> str:
        cmd_id = str(uuid.uuid4())
        payload = {
            "id": cmd_id,
            "action": action,
            "params": params or {},
            "ts": time.time(),
        }
        self._path("command.json").write_text(json.dumps(payload))
        return cmd_id

    def send_raw_lua(self, code: str) -> str:
        cmd_id = str(uuid.uuid4())
        payload = {
            "id": cmd_id,
            "action": "__raw__",
            "raw_lua": code,
            "ts": time.time(),
        }
        self._path("command.json").write_text(json.dumps(payload))
        return cmd_id

    def read_status(self) -> dict | None:
        p = self._path("status.json")
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return None

    def read_log(self) -> str:
        p = self._path("log.txt")
        if not p.exists():
            return ""
        try:
            return p.read_text()
        except Exception:
            return ""
