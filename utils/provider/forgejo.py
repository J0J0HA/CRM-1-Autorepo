from datetime import datetime

import aiohttp
import requests

from .. import datacls


async def get_repo(session: aiohttp.ClientSession,
                   settings: datacls.ModSettings) -> datacls.Repo:
    instance = (settings.instance or "https://codeberg.org").removesuffix("/")
    async with session.get(f"{instance}/api/v1/repos/{settings.repo}") as resp:
        repo_data = await resp.json()
    async with session.get(f"{instance}/api/v1/repos/{settings.repo}/commits",
                           timeout=10) as commits_resp:
        commits_data = await commits_resp.json()
    contributors = list(
        set(commit["commit"]["author"]["name"] for commit in commits_data))
    return datacls.Repo(
        name=repo_data["full_name"],
        git_url=repo_data["clone_url"],
        html_url=repo_data["html_url"],
        issue_url=repo_data["html_url"] + "/issues",
        owner=repo_data["owner"]["login"],
        authors=contributors,
        master_branch=repo_data["default_branch"],
    )


async def get_releases(session: aiohttp.ClientSession,
                       settings: datacls.ModSettings, repo: datacls.Repo):
    instance = (settings.instance or "https://codeberg.org").removesuffix("/")
    async with session.get(
            f"{instance}/api/v1/repos/{repo.name}/releases") as resp:
        releases_data = await resp.json()
    return [
        datacls.Release(
            tag=r["tag_name"],
            version=r["tag_name"].removeprefix("v").removeprefix("V"),
            title=r["name"],
            body=r["body"],
            attached_files=[(a["name"], a["browser_download_url"])
                            for a in r["assets"]],
            by=r["author"]["login"],
            published_at=datetime.strptime(r["published_at"].replace(":", ""),
                                           "%Y-%m-%dT%H%M%S%z").timestamp(),
            prerelease=r["prerelease"],
            link=r["html_url"],
            is_prebuilt=True,
        ) for r in releases_data
    ]


def get_latest_commit_as_release(settings: datacls.ModSettings,
                                 repo: datacls.Repo):
    """

    :param settings: datacls.ModSettings:
    :param repo: datacls.Repo:
    :param settings: datacls.ModSettings:
    :param repo: datacls.Repo:

    """
    instance = (settings.instance or "https://codeberg.org").removesuffix("/")
    resp = requests.get(f"{instance}/api/v1/repos/{repo.name}/commits")
    commits_data = resp.json()
    commit = commits_data[0]
    return datacls.Release(
        tag=commit["sha"],
        version="dev",
        title=commit["commit"]["message"].split("\n")[0],
        body=commit["commit"]["message"],
        attached_files=[],
        by=commit["commit"]["author"]["name"],
        published_at=datetime.strptime(commit["created"].replace(":", ""),
                                       "%Y-%m-%dT%H%M%S%z").timestamp(),
        prerelease=True,
        link=commit["html_url"],
        is_prebuilt=False,
    )
