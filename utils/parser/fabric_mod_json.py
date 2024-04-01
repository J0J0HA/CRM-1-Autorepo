from crm1.helpers.versions import range_from_maven_string
from crm1.spec import RDependency, RMod, UnsafeModExt

from ..data import ModSettings, Release, Repo


def parse_fabric_mod_json(
    settings: ModSettings, repo: Repo, data: dict, release: Release
) -> RMod:
    dependencies = {name: version for name, version in data.get("depends", {}).items()}
    return RMod(
        id=settings.id or data.get("id"),
        name=data.get("name") or settings.repo.rsplit("/", 1)[-1],
        desc=data.get("description") or "",
        authors=data.get("authors") or repo.authors or repo.owner,
        version=data.get("version"),
        game_version=(
            (
                range_from_maven_string(dependencies.get("cosmic_reach"))
                or range_from_maven_string(dependencies.get("cosmicreach"))
            ).to_string()
            if (dependencies.get("cosmic_reach") or dependencies.get("cosmicreach"))
            is not None
            else None
        ),
        url=release.attached_files[-1][1] if release.attached_files else release.link,
        deps=[
            RDependency(
                name,
                (
                    range_from_maven_string(version).to_string()
                    if version is not None
                    else None
                ),
                None,
            )
            for name, version in dependencies.items()
            if name != "fabricloader" and name != "cosmic_reach"
        ],
        ext=UnsafeModExt(
            modid=data.get("id"),
            icon=data.get("icon"),
            loader="fabric",
            loader_version=(
                range_from_maven_string(dependencies.get("fabricloader")).to_string()
                if dependencies.get("fabricloader") is not None
                else None
            ),
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
