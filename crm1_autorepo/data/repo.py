from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Repo:
    name: str
    git_url: str
    html_url: str
    issue_url: str
    owner: str
    authors: list[str]
    master_branch: str
