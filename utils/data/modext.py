from typing import Optional
from .dependency import Dependency

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class ModExt:
    modid: Optional[str] = None
    icon: Optional[str] = None
    loader: Optional[str] = None
    loader_version: Optional[str] = None
    source: Optional[str] = None
    issues: Optional[str] = None
    owner: Optional[str] = None
    changelog: Optional[str] = None
    published_at: Optional[str] = None
    alt_download: Optional[str] = None
    alt_versions: list["Mod"] = field(default_factory=list)
    suggests: Optional[dict[str, str]] = None
