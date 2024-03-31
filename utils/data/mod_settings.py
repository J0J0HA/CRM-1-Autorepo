from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from typing import Optional


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModSettings:
    provider: str
    repo: str
    folder: Optional[str] = None
    id: Optional[str] = None
    instance: Optional[str] = None
    dev_builds: bool = False
