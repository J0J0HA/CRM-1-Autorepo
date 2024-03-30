from datetime import datetime
from .. import datacls
import requests


def get_repo(settings: datacls.ModSettings) -> datacls.Repo:
    instance = (settings.instance or "https://codeberg.org").removesuffix("/")
    resp = requests.get(f"{instance}/api/v1/repos/{settings.repo}", timeout=10)
    repo_data = resp.json()
    commits_resp = requests.get(
        f"{instance}/api/v1/repos/{settings.repo}/commits", timeout=10
    )
    commits_data = commits_resp.json()
    contributors = list(set(commit["commit"]["author"]["name"] for commit in commits_data))
    return datacls.Repo(
        name=repo_data["full_name"],
        git_url=repo_data["clone_url"],
        html_url=repo_data["html_url"],
        issue_url=repo_data["html_url"] + "/issues",
        owner=repo_data["owner"]["login"],
        authors=contributors,
        master_branch=repo_data["default_branch"],
    )


def get_releases(settings: datacls.ModSettings, repo: datacls.Repo):
    instance = (settings.instance or "https://codeberg.org").removesuffix("/")
    resp = requests.get(f"{instance}/api/v1/repos/{repo.name}/releases", timeout=10)
    releases_data = resp.json()
    return [
        datacls.Release(
            tag=r["tag_name"],
            title=r["name"],
            body=r["body"],
            attached_files=[(a["name"], a["browser_download_url"]) for a in r["assets"]],
            by=r["author"]["login"],
            published_at=datetime.strptime(r["published_at"].replace(":", ""), "%Y-%m-%dT%H%M%S%z").timestamp(),
            prerelease=r["prerelease"],
            link=r["html_url"],
        )
        for r in releases_data
    ]
