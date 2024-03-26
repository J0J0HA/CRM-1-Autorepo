from dataclasses import dataclass
import re
import os
import time
from dataclasses_json import dataclass_json
import json
import hjson
from github import Github, Auth
import dotenv

dotenv.load_dotenv()

auth = Auth.Token(os.environ["GITHUB_TOKEN"])
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


def _parse_build_gradle(properties):
    properties = properties[properties.find("object Properties {") :]
    properties = properties[: properties.find("}")]
    properties = properties.replace("object Properties {", "").replace("}", "")
    properties_list = properties.split("\n")
    properties_list = [x.strip() for x in properties_list]
    result = {}
    for prop in properties_list:
        if prop:
            prop = prop.strip()
            key, value = prop.split("=")
            key = key.removeprefix("const ").removeprefix("val ").strip()
            value = value.strip().removeprefix('"').removesuffix('"')
            result[key.lower()] = value
    return result


def _parse_fabric_mod(props, mod_data):
    new_mod_data = {}
    for key, value in mod_data.items():
        if isinstance(value, str):

            def replace(match):
                replacement = match.group().removeprefix("${").removesuffix("}")
                if replacement in props:
                    replacement = props[replacement.lower()]
                else:
                    replacement = match.group()
                return replacement

            new_mod_data[key] = re.sub(r"\$\{.*?\}", replace, value)
            if key == "id" and not "." in new_mod_data[key]:
                new_mod_data[key] = props["maven_group"] + "." + new_mod_data[key]
        else:
            new_mod_data[key] = value
    return new_mod_data


def _generate_fabric_mod(settings, repo, latest_release, mod_json, properties):
    if properties:
        properties = properties.decoded_content.decode("utf-8")
        properties = _parse_build_gradle(properties)
    if mod_json:
        mod_data = json.loads(mod_json.decoded_content.decode("utf-8"))
        mod_data = _parse_fabric_mod(properties or {}, mod_data)
    else:
        mod_data = {}
    id_ = mod_data.get("id") or f"io.github.{repo.owner.login}.{repo.name}"
    name = mod_data.get("name") or repo.name
    desc = mod_data.get("description") or repo.description
    authors = mod_data.get("authors") or [
        repo.owner.login,
        *[c.login for c in repo.get_contributors()],
    ]
    version = mod_data.get("version") or latest_release.tag_name
    depends = {
        key: value.removeprefix(">=")
        for key, value in _parse_fabric_mod(
            properties, mod_data.get("depends") or {}
        ).items()
    }
    print(depends)
    game_version = "0.0.0"
    if "cosmic_reach" in depends:
        game_version = depends["cosmic_reach"]
        del depends["cosmic_reach"]
    fabricloader = "0.0.0"
    if "fabricloader" in depends:
        fabricloader = depends["fabricloader"]
        del depends["fabricloader"]
    deps = []
    for thing, version in depends.items():
        deps.append(Dependency(id=thing, version=version, source="unknown"))
    downloads = latest_release.get_assets()
    downloads = [x for x in downloads if x.name.endswith(".jar")]
    downloads = sorted(downloads, key=lambda x: x.created_at, reverse=True)
    return Mod(
        id=id_,
        name=name,
        desc=desc,
        authors=authors,
        version=version,
        game_version=game_version,
        url=downloads[0].browser_download_url if downloads else None,
        deps=deps,
        ext={"fabricloader": fabricloader},
    )


def _gh_get_repo(settings):
    repo = g.get_repo(settings["repo"])
    latest_release = repo.get_latest_release()
    if settings.get("folder"):
        folder = settings["folder"].strip("/")
    if settings["type"] == "fabric":
        try:
            mod_json = repo.get_contents(
                f"{folder}/src/main/resources/fabric.mod.json",
                ref=latest_release.tag_name,
            )
        except Exception as e:
            print(f"WARNING: FAIL on {settings['repo']}, MODFILE NOT FOUND: ", e)
            mod_json = None
        try:
            properties = repo.get_contents(
                f"{folder}/build.gradle.kts", ref=latest_release.tag_name
            )
        except Exception as e:
            print(f"WARNING: FAIL on {settings['repo']}, PROPERTIES NOT FOUND: ", e)
            properties = None
        return _generate_fabric_mod(
            settings, repo, latest_release, mod_json, properties
        )


def get_repo(settings):
    if settings["provider"] == "github":
        return _gh_get_repo(settings)
    raise ValueError("Unknown provider")


def main():
    with open("from_repos.json", "r", encoding="utf-8") as f:
        settings = json.load(f)
    final_repos = []
    for repo in settings["repos"]:
        mod = get_repo(repo)
        final_repos.append(mod.to_dict())

    out = {
        "specVersion": 1,
        "rootId": settings["rootId"],
        "lastUpdated": round(time.time()),
        "mods": final_repos,
    }

    with open("repo.hjson", "w", encoding="utf-8") as f:
        hjson.dump(out, f)


if __name__ == "__main__":
    main()
