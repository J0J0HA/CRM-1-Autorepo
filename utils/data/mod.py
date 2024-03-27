from .dependency import Dependency

from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Mod:
    id: str
    name: str
    desc: str
    authors: list[str]
    version: str
    game_version: str
    url: str
    deps: list[Dependency]
    ext: dict
