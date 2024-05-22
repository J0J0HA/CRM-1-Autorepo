import os
import pathlib

from crm1.helpers.versions import Version, range_from_maven_string
from crm1.spec.v2 import CommonModExt, RDependency, RMod
from loguru import logger

from ..data import ModSettings, Release, Repo


def parse_quilt_mod_json(
    base_address: str,
    settings: ModSettings,
    repo: Repo,
    data: dict,
    jardir: pathlib.Path,
    release: Release,
) -> RMod:
    loader_data = data.get("quilt_loader", {})
    dependencies = {
        item["id"]: item["versions"] for item in loader_data.get("depends", [])
    }
    suggests = {
        item["id"]: item["versions"] for item in loader_data.get("suggests", [])
    }
    metadata = loader_data.get("metadata", {})
    id_ = (
        (loader_data.get("group") + "." + loader_data.get("id"))
        if loader_data.get("group") is not None
        else "io.github." + repo.owner + "." + loader_data.get("id")
    )
    icon_path = (
        (
            base_address
            + (jardir.relative_to(os.getcwd()) / metadata.get("icon")).as_posix()
        )
        if metadata.get("icon")
        else None
    )

    try:
        deps = [
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
            if name != "cosmicquilt"
            and name != "cosmicreach"
            and name != "cosmic_quilt"
            and name != "cosmic_reach"
        ]
    except Exception as e:
        logger.error(f"Error parsing dependencies for {id_}", e, exc_info=True)
        return None
    
    if (version := loader_data.get("version")) is not None:
        try:
            Version.from_string(version)
        except Exception as e:
            logger.error(f"Error parsing version {version} for {id_}", e, exc_info=True)
            logger.info("This typically means the version format is not using semantic versioning. This is a problem, because comparing versions automatically is no longer possible.")
            logger.warning("Version will be skipped!")
            return None

    return RMod(
        id=settings.id or id_,
        name=metadata.get("name") or settings.repo.rsplit("/", 1)[-1],
        desc=metadata.get("description") or "",
        authors=metadata.get("contributors", {}).keys() or repo.authors or repo.owner,
        version=loader_data.get("version"),
        game_version=(
            range_from_maven_string(
                dependencies.get("cosmicreach") or dependencies.get("cosmic_reach")
            ).to_string()
            if (dependencies.get("cosmicreach") or dependencies.get("cosmic_reach"))
            is not None
            else None
        ),
        url=release.attached_files[0][1] if release.attached_files else release.link,
        deps=deps,
        ext=CommonModExt(
            modid=loader_data.get("id"),
            icon=icon_path,
            loader="quilt",
            loader_version=(
                range_from_maven_string(
                    dependencies.get("cosmicquilt") or dependencies.get("cosmic_quilt")
                ).to_string()
                if (dependencies.get("cosmicquilt") or dependencies.get("cosmic_quilt"))
                is not None
                else None
            ),
            source=repo.html_url,
            issues=repo.issue_url,
            owner=repo.owner,
            changelog=release.link,
            alt_download=release.attached_files,
            alt_versions=[],
            published_at=release.published_at,
            suggests=[
                RDependency(
                    name,
                    (
                        range_from_maven_string(version).to_string()
                        if version is not None
                        else None
                    ),
                    None,
                )
                for name, version in suggests.items()
            ],
            prerelease=release.prerelease,
        ),
    )
