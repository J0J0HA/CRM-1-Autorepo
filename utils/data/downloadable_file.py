from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class DownloadableFile:
    name: str
    url: str
    download_count: int
