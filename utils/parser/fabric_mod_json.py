import os
import pathlib

from crm1.helpers.versions import Version, range_from_maven_string
from crm1.spec.v2 import CommonModExt, RDependency, RMod
from loguru import logger

from ..data import ModSettings, Release, Repo


def parse_fabric_mod_json(
    base_address: str,
    settings: ModSettings,
    repo: Repo,
    data: dict,
    jardir: pathlib.Path,
    release: Release,
) -> RMod:
    dependencies = {name: version for name, version in data.get("depends", {}).items()}
    icon_path = (
        (base_address + (jardir.relative_to(os.getcwd()) / data.get("icon")).as_posix())
        if data.get("icon")
        else None
    )

    if (version := data.get("version")) is not None:
        try:
            Version.from_string(version)
        except Exception as e:
            logger.error(f"Error parsing version {version} for {settings.id or data.get('id')}", e, exc_info=True)
            logger.info(
                "This typically means the version format is not using semantic versioning. This is a problem, because comparing versions automatically is no longer possible."
            )
            logger.warning("Version will be skipped!")
            return None

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
        url=release.attached_files[0][1] if release.attached_files else release.link,
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
        ext=CommonModExt(
            modid=data.get("id"),
            icon=icon_path,
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
