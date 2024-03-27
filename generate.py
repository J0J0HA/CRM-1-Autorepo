from dataclasses import dataclass
import re
import os
import time
from dataclasses_json import dataclass_json
import json
import hjson
from github import Github, Auth
import environs


env = environs.Env()
env.read_env()

auth = Auth.Token(env("GITHUB_TOKEN"))
g = Github(auth=auth)


@dataclass_json
@dataclass
class Dependency:
    id: str
    version: str
    source: str


@dataclass_json
@dataclass
class Mod:
    id: str
    name: str
    desc: str
    authors: list[str]
    version: str
    game_version: str
    url: str
    deps: list[Dependency]
    ext: dict


@dataclass_json
@dataclass
class ModMetaless:
    version: str
    game_version: str
    url: str
    deps: list[Dependency]
    ext: dict


def _parse_build_gradle_kts(content):
    properties_obj = content[content.find("object Properties {") :]
    properties_obj = properties_obj[: properties_obj.find("}")]
    properties_obj = properties_obj.removeprefix("object Properties {").removesuffix(
        "}"
    )
    properties_obj_list = properties_obj.split("\n")
    properties_obj_list = [x.strip() for x in properties_obj_list]
    properties_obj_result = {}
    for prop in properties_obj_list:
        if prop:
            prop = prop.strip()
            key, value = prop.split("=")
            key = key.removeprefix("const ").removeprefix("val ").strip()
            value = value.strip().removeprefix('"').removesuffix('"')
            properties_obj_result[key] = value
    properties_val = content[content.find("val properties = mapOf(") :]
    properties_val = properties_val[: properties_val.find(")")]
    properties_val = properties_val.removeprefix(
        "val properties = mapOf("
    ).removesuffix(")")
    properties_val_list = properties_val.split(",")
    properties_val_list = [x.strip() for x in properties_val_list]
    properties_val_result = {}
    for prop in properties_val_list:
        if prop:
            prop = prop.strip()
            key, value = prop.split(" to ")
            key = key.removeprefix('"').removesuffix('"')
            value = value.removeprefix("Properties.")
            properties_val_result[key] = properties_obj_result[value]
    return properties_val_result


def _parse_gradle_properties(content):
    properties = {}
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=")
            key = key.strip()
            value = value.strip()
            properties[key] = value
    return properties


def _parse_fabric_mod(props, mod_data):
    new_mod_data = {}
    for key, value in mod_data.items():
        if isinstance(value, str):

            def replace(match):
                replacement = match.group().removeprefix("${").removesuffix("}")
                if replacement in props:
                    replacement = props[replacement]
                else:
                    replacement = match.group()
                return replacement

            new_mod_data[key] = re.sub(r"\$\{.*?\}", replace, value)
        else:
            new_mod_data[key] = value
    return new_mod_data


def _generate_fabric_mod(
    settings, repo_data, latest_release, mod_json, properties, skip_meta=False
):
    if mod_json:
        mod_data = json.loads(mod_json.decoded_content.decode("utf-8"))
        mod_data = _parse_fabric_mod(properties or {}, mod_data)
    else:
        mod_data = {}
    # pre: mod_data.get("id") or
    id_ = (
        properties.get("maven_group")
        or f"io.github.{repo_data['owner']}.{repo_data['name']}"
    )
    if settings.get("id"):
        id_ = settings["id"]
    name = mod_data.get("name") or repo_data["name"]
    desc = mod_data.get("description") or repo_data["desc"]
    authors = mod_data.get("authors") or repo_data["contributors"]
    # pre: mod_data.get("version") or
    version = (
        latest_release if isinstance(latest_release, str) else latest_release.tag_name
    ).removeprefix("v")
    depends = {
        key: value.removeprefix(">=")
        for key, value in _parse_fabric_mod(
            properties, mod_data.get("depends") or {}
        ).items()
    }
    game_version = "0.0.0"
    if "cosmic_reach" in depends:
        game_version = depends["cosmic_reach"]
        del depends["cosmic_reach"]
    fabricloader = "0.0.0"
    if "fabricloader" in depends:
        fabricloader = depends["fabricloader"]
        del depends["fabricloader"]
    deps = []

    icon_url = mod_data.get("icon") or None
    print(icon_url)
    if icon_url and (
        not icon_url.startswith("http://") and not icon_url.startswith("https://")
    ):
        icon_url = icon_url.strip("/")
        icon_url = f"https://raw.githubusercontent.com/{settings['repo']}/{latest_release.tag_name}/{settings['folder']}/serc/main/resources/{icon_url}"

    for thing, version in depends.items():
        deps.append(Dependency(id=thing, version=version, source="unknown"))
    if settings.get("deps"):
        for dep in settings["deps"]:
            deps.append(
                Dependency(id=dep["id"], version=dep["version"], source=dep["source"])
            )
    if not isinstance(latest_release, str):
        downloads = latest_release.get_assets()
        downloads = [x for x in downloads if x.name.endswith(".jar")]
        downloads = sorted(downloads, key=lambda x: len(x.name))
    else:
        downloads = []
    if skip_meta:
        return ModMetaless(
            version=version,
            game_version=game_version,
            url=downloads[0].browser_download_url if downloads else None,
            deps=deps,
            ext={
                "fabricloader": fabricloader,
                "loader": "fabric",
                "alt_downloads": (
                    [x.browser_download_url for x in downloads[1:]]
                    if downloads
                    else None
                ),
                "changelog": repo_data["changelog"],
            },
        )
    return Mod(
        id=id_,
        name=name,
        desc=desc,
        authors=authors,
        version=version,
        game_version=game_version,
        url=downloads[0].browser_download_url if downloads else None,
        deps=deps,
        ext={
            "icon": icon_url,
            "fabricloader": fabricloader,
            "loader": "fabric",
            "altDownloads": (
                [x.browser_download_url for x in downloads[1:]] if downloads else None
            ),
            "source": repo_data["source"],
            "issues": repo_data["issues"],
            "owner": repo_data["owner"],
            "changelog": repo_data["changelog"],
        },
    )


def _gh_get_mod(settings):
    repo = g.get_repo(settings["repo"])
    if settings.get("tag") is not None:
        if settings["tag"] == False:
            latest_release = None
        else:
            latest_release = repo.get_release(settings["tag"])
    else:
        try:
            latest_release = repo.get_latest_release()
        except:
            releases = repo.get_releases()
            releases = sorted(releases, key=lambda x: x.created_at, reverse=True)
            latest_release = releases[0]
    if settings.get("folder"):
        folder = settings["folder"].strip("/") + "/"
    repo_data = {}
    repo_data["issues"] = f"{repo.html_url}/issues"
    repo_data["source"] = repo.html_url
    repo_data["owner"] = repo.owner.login
    repo_data["name"] = repo.name
    repo_data["desc"] = repo.description
    repo_data["contributors"] = [x.login for x in repo.get_contributors()]
    repo_data["changelog"] = latest_release.body if latest_release else None

    if settings["type"] == "fabric":
        try:
            mod_json = repo.get_contents(
                f"{folder}src/main/resources/fabric.mod.json",
                ref=(
                    latest_release.tag_name
                    if latest_release
                    else settings.get("branch")
                ),
            )
        except Exception as e:
            print(f"WARNING: FAIL on {settings['repo']}, MODFILE NOT FOUND: ", e)
            mod_json = None
        try:
            properties = repo.get_contents(
                f"{folder}build.gradle.kts",
                ref=(
                    latest_release.tag_name
                    if latest_release
                    else settings.get("branch")
                ),
            )
            if properties:
                properties = properties.decoded_content.decode("utf-8")
                properties = _parse_build_gradle_kts(properties)
        except Exception as e:
            try:
                properties = repo.get_contents(
                    f"{folder}gradle.properties",
                    ref=(
                        latest_release.tag_name
                        if latest_release
                        else settings.get("branch")
                    ),
                )
                if properties:
                    properties = properties.decoded_content.decode("utf-8")
                    properties = _parse_gradle_properties(properties)
            except Exception as e:
                print(f"WARNING: FAIL on {settings['repo']}, PROPERTIES NOT FOUND: ", e)
                properties = {}

        older_releases = repo.get_releases()
        older_releases = [
            x for x in older_releases if x.tag_name != latest_release.tag_name
        ]
        older_releases = sorted(
            older_releases, key=lambda x: x.created_at, reverse=True
        )

        older_mods = []

        for release in older_releases:

            specific_repo_data = repo_data.copy()
            specific_repo_data["changelog"] = release.body

            try:
                specific_mod_json = repo.get_contents(
                    f"{folder}src/main/resources/fabric.mod.json", ref=release.tag_name
                )
            except Exception as e:
                print(f"WARNING: FAIL on {settings['repo']}, MODFILE NOT FOUND: ", e)
                specific_mod_json = None
            try:
                specific_properties = repo.get_contents(
                    f"{folder}build.gradle.kts", ref=release.tag_name
                )
                if specific_properties:
                    specific_properties = specific_properties.decoded_content.decode(
                        "utf-8"
                    )
                    specific_properties = _parse_build_gradle_kts(specific_properties)
            except Exception as e:
                try:
                    specific_properties = repo.get_contents(
                        f"{folder}gradle.properties", ref=release.tag_name
                    )
                    if specific_properties:
                        specific_properties = (
                            specific_properties.decoded_content.decode("utf-8")
                        )
                        specific_properties = _parse_gradle_properties(
                            specific_properties
                        )
                except Exception as e:
                    print(
                        f"WARNING: FAIL on {settings['repo']}, PROPERTIES NOT FOUND: ",
                        e,
                    )
                    specific_properties = {}

            older_mods.append(
                _generate_fabric_mod(
                    settings,
                    specific_repo_data,
                    release,
                    specific_mod_json,
                    specific_properties,
                    skip_meta=True,
                )
            )

        mod = _generate_fabric_mod(
            settings,
            repo_data,
            latest_release if latest_release else settings.get("branch"),
            mod_json,
            properties,
        )

        if older_mods:
            mod.ext["altVersions"] = older_mods
        return mod


def get_mod(settings):
    if settings["provider"] == "github":
        return _gh_get_mod(settings)
    raise ValueError("Unknown provider")


def main():
    with open("settings.json", "r", encoding="utf-8") as f:
        settings = json.load(f)
    final_repos = []
    for repo in settings["repos"]:
        mod = get_mod(repo)
        final_repos.append(mod.to_dict())

    out = {
        "specVersion": 1,
        "rootId": settings["rootId"],
        "lastUpdated": round(time.time()),
        "mods": final_repos,
    }

    with open("repo.hjson", "w", encoding="utf-8") as f:
        hjson.dump(out, f)

    with open("repo.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4)


if __name__ == "__main__":
    main()
