from ..data import Mod, Release, ModSettings, ModExt, Dependency, Repo


def parse_fabric_mod_json(
    settings: ModSettings, repo: Repo, data: dict, release: Release
) -> Mod:
    dependencies = {name: version for name, version in data.get("depends", {}).items()}
    return Mod(
        id=settings.id or data.get("id"),
        name=data.get("name") or settings.repo.rsplit("/", 1)[-1],
        desc=data.get("description") or "",
        authors=data.get("authors") or repo.authors or repo.owner,
        version=data.get("version"),
        game_version=dependencies.get("cosmic_reach"),
        url=release.attached_files[-1][1] if release.attached_files else release.link,
        deps=[
            Dependency(name, version, None)
            for name, version in dependencies.items()
            if name != "fabricloader" and name != "cosmic_reach"
        ],
        ext=ModExt(
            modid=data.get("id"),
            icon=data.get("icon"),
            loader="fabric",
            loader_version=dependencies.get("fabricloader"),
            source=repo.html_url,
            issues=repo.issue_url,
            owner=repo.owner,
            changelog=release.link,
            alt_download=release.attached_files,
            alt_versions=[],
            published_at=release.published_at,
            prerelease=release.prerelease,
        ),
    )
