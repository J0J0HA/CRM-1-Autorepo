from ..data import Mod, Release, ModSettings, ModExt, Dependency, Repo


def parse_fabric_mod_json(
    settings: ModSettings, repo: Repo, data: dict, release: Release
) -> Mod:
    dependencies = {
        name: version.removeprefix(">").removeprefix("<").removeprefix("=")
        for name, version in data.get("depends", {}).items()
    }
    files = sorted(release.attached_files, key=lambda f: len(f[0]))
    return Mod(
        id=settings.id or data.get("id"),
        name=data.get("name") or settings.repo.rsplit("/", 1)[-1],
        desc=data.get("description") or "",
        authors=data.get("authors") or repo.authors or repo.owner,
        version=data.get("version") or release.tag.removeprefix("v"),
        game_version=dependencies.get("cosmic_reach"),
        url=files[-1][1] if files else release.link,
        deps=[
            Dependency(name, version, None)
            for name, version in dependencies.items()
            if name != "fabricloader" and name != "cosmic_reach"
        ],
        ext=ModExt(
            icon=data.get("icon"),
            loader="fabric",
            loader_version=dependencies.get("fabricloader"),
            source=repo.html_url,
            issues=repo.issue_url,
            owner=repo.owner,
            changelog=release.link,
            alt_download=files,
            alt_versions=[],
        ),
    )
