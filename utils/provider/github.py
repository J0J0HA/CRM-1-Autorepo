from functools import lru_cache

import environs
from github import Auth
from github import Github

from .. import datacls

env = environs.Env()
env.read_env()

auth = Auth.Token(env("GITHUB_TOKEN"))
g = Github(auth=auth)

g_get_repo = lru_cache(maxsize=128)(g.get_repo)


async def get_repo(session, settings: datacls.ModSettings) -> datacls.Repo:
    repo = g_get_repo(settings.repo)
    return datacls.Repo(
        name=repo.full_name,
        git_url=repo.clone_url,
        html_url=repo.html_url,
        issue_url=repo.html_url + "/issues",
        owner=repo.owner.login,
        authors=[c.login for c in repo.get_contributors()],
        master_branch=repo.default_branch,
    )


async def get_releases(session, settings: datacls.ModSettings, repo: datacls.Repo):
    return [
        datacls.Release(
            tag=r.tag_name,
            version=r.tag_name.removeprefix("v").removeprefix("V"),
            title=r.title,
            body=r.body,
            attached_files=[(a.name, a.browser_download_url) for a in r.get_assets()],
            by=r.author.login,
            published_at=r.published_at.timestamp(),
            prerelease=r.prerelease,
            link=r.html_url,
        )
        for r in g_get_repo(settings.repo).get_releases()
    ]


def get_latest_commit_as_release(settings: datacls.ModSettings, repo: datacls.Repo):
    """

    :param settings: datacls.ModSettings:
    :param repo: datacls.Repo:
    :param settings: datacls.ModSettings:
    :param repo: datacls.Repo:

    """
    latest_commit = g_get_repo(settings.repo).get_commits()[0]
    return datacls.Release(
        tag=latest_commit.sha,
        version="dev",
        title=latest_commit.commit.message.split("\n")[0],
        body=latest_commit.commit.message,
        attached_files=[],
        by=latest_commit.author.login,
        published_at=latest_commit.commit.author.date.timestamp(),
        prerelease=True,
        link=latest_commit.html_url,
        is_prebuilt=False,
    )
