from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from typing import Optional, Union


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModSettings:
    provider: str
    repo: str
    folder: Optional[str] = None
    id: Optional[str] = None
    instance: Optional[str] = None
    dev_builds: bool = False
