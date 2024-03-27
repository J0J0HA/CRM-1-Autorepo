from utils import (
    datacls,
    ClonedRepo,
    provider as providers,
    parser as parsers,
    replace_vars,
)
import json
import hjson


def get_mod(settings: datacls.ModSettings) -> datacls.Mod:
    provider = providers.map[settings.provider]
    versions = {}

    repo = provider.get_repo(settings.repo)

    with ClonedRepo(repo.git_url) as clone:
        for rel in provider.get_releases(repo):
            version = rel.tag.removeprefix("v")
            print(f"Loading {settings.repo} {version}...")
            clone.repo.git.checkout(rel.tag)
            properties = {}
            if clone["gradle.properties"].exists():
                with clone.open("gradle.properties") as f:
                    properties.update(parsers.parse_gradle_properties(f.read()))
            elif clone["build.gradle.kts"].exists():
                with clone.open("build.gradle.kts") as f:
                    properties.update(parsers.parse_build_gradle_kts(f.read()))

            if not clone["src/main/resources"].exists():
                print(
                    f"Skipping {settings.repo} {version} because it doesn't have resources."
                )
                continue
            mod = None
            if clone["src/main/resources/fabric.mod.json"].exists():
                with clone.open("src/main/resources/fabric.mod.json") as f:
                    json_content = f.read()
                    json_vars = replace_vars(json_content, properties)
                    json_data = json.loads(json_vars)
                mod = parsers.parse_fabric_mod_json(settings, repo, json_data, rel)
            else:
                print(
                    f"Skipping {settings.repo} {version} because it doesn't have a fabric.mod.json."
                )
                continue

            if version in versions:
                print(
                    f"Skipping {settings.repo} {version} because it's already loaded."
                )
                continue
            versions[version] = mod

    biggest_version = max(versions.keys(), key=lambda v: len(v))
    other_versions = [v for v in versions if v != biggest_version]
    mod = versions[biggest_version]
    mod.ext.alt_versions = [versions[v] for v in other_versions]
    return mod


def main():
    with open("settings.json", "r", encoding="utf-8") as f:
        setts = json.load(f)

    mods = [get_mod(datacls.ModSettings.from_dict(mod)) for mod in setts["repos"]]

    file_content = {
        **{f"_note_{name}": value for name, value in setts["notes"].items()},
        "specVersion": 1,
        "rootId": setts["rootId"],
        "mods": [mod.to_dict() for mod in mods],
    }

    with open("repo.json", "w", encoding="utf-8") as f:
        json.dump(
            file_content,
            f,
            indent=4,
        )

    with open("repo.hjson", "w", encoding="utf-8") as f:
        hjson.dump(
            file_content,
            f,
            indent=4,
        )


if __name__ == "__main__":
    main()
