from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Release:
    tag: str
    version: str
    title: str
    body: str
    attached_files: list[tuple[str, str]]
    by: str
    published_at: int
    prerelease: bool
    link: str
    is_prebuilt: bool = True
