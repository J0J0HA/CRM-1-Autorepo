from github import Github, Auth
from .. import datacls
import environs


env = environs.Env()
env.read_env()

auth = Auth.Token(env("GITHUB_TOKEN"))
g = Github(auth=auth)


def get_repo(settings: datacls.ModSettings) -> datacls.Repo:
    repo = g.get_repo(settings.repo)
    return datacls.Repo(
        name=repo.full_name,
        git_url=repo.clone_url,
        html_url=repo.html_url,
        issue_url=repo.html_url + "/issues",
        owner=repo.owner.login,
        authors=[c.login for c in repo.get_contributors()],
        master_branch=repo.default_branch,
    )


def get_releases(settings: datacls.ModSettings, repo: datacls.Repo):
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
        for r in g.get_repo(repo.name).get_releases()
    ]


def get_latest_commit_as_release(settings: datacls.ModSettings, repo: datacls.Repo):
    latest_commit = g.get_repo(repo.name).get_commits()[0]
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
