import time
from utils import (
    datacls,
    ClonedRepo,
    provider as providers,
    parser as parsers,
    replace_vars,
)
import requests
from loguru import logger
import json
import sys
import hjson


logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> <blue>|</blue> <lvl>{level:<7}</lvl> <blue>|</blue> <lvl>{message}</lvl>",
    level="INFO",
    colorize=True,
)
logger.add(
    "main.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | {message}",
    level="INFO",
    colorize=False,
)


def get_mod(settings: datacls.ModSettings) -> datacls.Mod:
    provider = providers.map[settings.provider]
    versions = {}

    logger.info(f"[{settings.repo}] Loading Metadata...")
    repo = provider.get_repo(settings.repo)
    releases = provider.get_releases(repo)
    if not releases:
        logger.warning(
            f"[{settings.repo}] Skipping because it doesn't have any releases."
        )
        return None

    logger.info(f"[{settings.repo}] Cloning repository...")
    with ClonedRepo(repo.git_url) as clone:
        for rel in releases:
            version = rel.tag.removeprefix("v")
            logger.info(f"[{settings.repo}] [v{version}] Loading Metadata...")
            clone.repo.git.checkout(rel.tag)
            properties = {}
            if clone["gradle.properties"].exists():
                with clone.open("gradle.properties") as f:
                    properties.update(parsers.parse_gradle_properties(f.read()))
            elif clone["build.gradle.kts"].exists():
                with clone.open("build.gradle.kts") as f:
                    properties.update(parsers.parse_build_gradle_kts(f.read()))

            if not clone["src/main/resources"].exists():
                logger.warning(
                    f"[{settings.repo}] [v{version}] Skipping because it doesn't have resources."
                )
                continue
            mod = None
            if clone["cosmicreach-mod.json"].exists():
                with clone.open("cosmicreach-mod.json") as f:
                    json_content = f.read()
                    json_vars = replace_vars(json_content, properties)
                    json_data = json.loads(json_vars)
                mod = parsers.parse_fabric_mod_json(settings, repo, json_data, rel)
            elif clone["src/main/resources/fabric.mod.json"].exists():
                with clone.open("src/main/resources/fabric.mod.json") as f:
                    json_content = f.read()
                    json_vars = replace_vars(json_content, properties)
                    json_data = json.loads(json_vars)
                mod = parsers.parse_fabric_mod_json(settings, repo, json_data, rel)
            else:
                logger.warning(
                    f"[{settings.repo}] [v{version}] Skipping because it doesn't have a parsable config file."
                )
                continue

            if version in versions:
                logger.warning(
                    f"[{settings.repo}] [v{version}] Skipping because it's already added."
                )
                continue
            versions[version] = mod

    if not versions:
        logger.warning(
            f"[{settings.repo}] Skipping because it doesn't have any versions."
        )
        return None

    logger.info(f"[{settings.repo}] Finalizing...")
    biggest_version = max(versions.keys(), key=lambda v: len(v))
    other_versions = [v for v in versions if v != biggest_version]
    mod = versions[biggest_version]
    mod.ext.alt_versions = [versions[v] for v in other_versions]
    logger.success(f"[{settings.repo}] Mod loaded.")
    return mod


def generate_repo(setts):
    logger.info("Loading Mods...")
    mods = [
        omod
        for omod in (
            get_mod(datacls.ModSettings.from_dict(mod)) for mod in setts["mods"]
        )
        if omod
    ]

    logger.info("Generating output content...")
    file_content = {
        **{f"_note_{name}": value for name, value in setts["notes"].items()},
        "specVersion": 1,
        "lastUpdated": round(time.time() * 1000),
        "rootId": setts["rootId"],
        "mods": [mod.to_dict() for mod in mods],
    }

    logger.info("Writing output files...")
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

    logger.success("Generated repo.")


def generate_repo_mapping(repos):
    logger.info("Generating repo mapping...")

    repo_results = {}
    mods = {}
    for repo_address in repos:
        logger.info(f"[{repo_address}] Loading metadata...")
        try:
            resp = requests.get(repo_address, timeout=10)
            res = hjson.loads(resp.text)
        except Exception as e:
            logger.error(f"[{repo_address}] Failed to load metadata: {e}")
            continue
        if "rootId" not in res:
            logger.warning(f"[{repo_address}] Skipping because it doesn't have a rootId.")
            continue
        repo_id = res["rootId"]
        if not repo_id:
            logger.warning(f"[{repo_address}] Skipping because rootId is empty.")
            continue
        if "mods" not in res:
            logger.warning(f"[{repo_id}] Skipping because it doesn't have mods.")
            continue
        repo_results[repo_id] = res["mods"]
        
    repo_results = {k: v for k, v in sorted(repo_results.items(), key=lambda item: len(item[1]), reverse=True)}
    
    for repo_id, repo_mods in repo_results.items():
        logger.info(f"[{repo_id}] Processing mods...")
        for mod in repo_mods:
            if "id" not in mod:
                logger.warning(f"[{repo_id}] Skipping MOD because mod doesn't have an id.")
                continue
            if mod["id"] not in mods:
                mods[mod["id"]] = []
            mods[mod["id"]].append(repo_id)

    logger.info("Generating output content...")

    output_content = {
        "mods": mods,
        "repos": repos,
        "lastUpdated": round(time.time() * 1000),
    }

    logger.info("Writing output files...")

    with open("repo_mapping.json", "w", encoding="utf-8") as f:
        json.dump(
            output_content,
            f,
            indent=4,
        )

    with open("repo_mapping.hjson", "w", encoding="utf-8") as f:
        hjson.dump(
            output_content,
            f,
            indent=4,
        )

    logger.success("Generated repo mapping.")


@logger.catch
def main():
    start = time.time()
    logger.info("Reading config...")
    with open("settings.json", "r", encoding="utf-8") as f:
        setts = json.load(f)
    generate_repo(setts)
    generate_repo_mapping(setts["repos"])
    logger.success(f"Finished. Took {time.time() - start:.2f}s.")


if __name__ == "__main__":
    main()
