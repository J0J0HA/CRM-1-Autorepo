from dataclasses import dataclass
from typing import Optional

from dataclasses_json import LetterCase, dataclass_json


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ModSettings:
    provider: str
    repo: str
    folder: Optional[str] = None
    id: Optional[str] = None
    instance: Optional[str] = None
    dev_builds: bool = False
