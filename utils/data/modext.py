from .dependency import Dependency

from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class ModExt:
    icon: str = None
    loader: str = None
    loader_version: str = None
    source: str = None
    issues: str = None
    owner: str = None
    changelog: str = None
    published_at: str = None
    alt_download: str = None
    alt_versions: list["Mod"] = None
    suggests: dict[str, str] = None
