from github import Github, Auth
from .. import datacls
import environs


env = environs.Env()
env.read_env()

auth = Auth.Token(env("GITHUB_TOKEN"))
g = Github(auth=auth)


def get_repo(repo_name: str) -> datacls.Repo:
    repo = g.get_repo(repo_name)
    return datacls.Repo(
        name=repo.full_name,
        git_url=repo.clone_url,
        html_url=repo.html_url,
        issue_url=repo.html_url + "/issues",
        owner=repo.owner.login,
        authors=[c.login for c in repo.get_contributors()],
        master_branch=repo.default_branch,
    )


def get_releases(repo: datacls.Repo):
    return [
        datacls.Release(
            tag=r.tag_name,
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
