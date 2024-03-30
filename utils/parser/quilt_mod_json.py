from ..data import Mod, Release, ModSettings, ModExt, Dependency, Repo


def parse_quilt_mod_json(
    settings: ModSettings, repo: Repo, data: dict, release: Release
) -> Mod:
    loader_data = data.get("quilt_loader", {})
    dependencies = {
        item["id"]: item["versions"]
        for item in loader_data.get("depends", [])
    }
    suggests = {
        item["id"]: item["versions"]
        for item in loader_data.get("suggests", [])
    }
    metadata = loader_data.get("metadata", {})
    files = sorted(release.attached_files, key=lambda f: len(f[0]))
    id_ = (loader_data.get("group") + "." + loader_data.get("id")) if loader_data.get("group") is not None else loader_data.get("id")
    return Mod(
        id=settings.id or id_,
        name=metadata.get("name") or settings.repo.rsplit("/", 1)[-1],
        desc=metadata.get("description") or "",
        authors=metadata.get("contributors", {}).keys() or repo.authors or repo.owner,
        version=loader_data.get("version") or release.tag.removeprefix("v").removeprefix("V"),
        game_version=dependencies.get("cosmic_reach"),
        url=files[-1][1] if files else release.link,
        deps=[
            Dependency(name, version, None)
            for name, version in dependencies.items()
            if name != "cosmic_quilt" and name != "cosmic_reach"
        ],
        ext=ModExt(
            icon=metadata.get("icon"),
            loader="quilt",
            loader_version=dependencies.get("cosmic_quilt"),
            source=repo.html_url,
            issues=repo.issue_url,
            owner=repo.owner,
            changelog=release.link,
            alt_download=files,
            alt_versions=[],
            published_at=release.published_at,
            suggests=suggests,
        ),
    )
