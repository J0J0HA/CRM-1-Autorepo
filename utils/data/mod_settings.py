from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Optional


@dataclass_json
@dataclass
class ModSettings:
    provider: str
    repo: str
    folder: Optional[str] = None
    id: Optional[str] = None
