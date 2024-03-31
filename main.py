import os
import asyncio
import aiohttp
import time
from typing import Optional
from utils import (
    datacls,
    ClonedRepo,
    provider as providers,
    parser as parsers,
    UnzippedJar,
    download_jar,
)
import requests
from loguru import logger
import json
import sys
import hjson


logger.remove()
logger.add(
    sys.stderr,
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


async def get_repo_jarpath(
    session: aiohttp.ClientSession,
    main_address: str,
    settings: datacls.ModSettings,
    repo: datacls.Repo,
    release: datacls.Release,
) -> Optional[str]:
    if not release.is_prebuilt:
        logger.info(f"[{settings.repo}] [{release.version}] Cloning repository...")
        with ClonedRepo(repo.git_url, ref=release.tag, no_delete=True) as clone:
            cur_dir = os.getcwd()
            os.chdir(clone.dir)
            logger.info(f"[{settings.repo}] [{release.version}] Building jar...")
            ret_val = os.system("gradle build")
            if ret_val != 0:
                logger.warning(
                    f"[{settings.repo}] [{release.version}] Skipping because build failed. (Invalid return value)"
                )
                os.chdir(cur_dir)
                return
            if not clone.path("build/libs").exists():
                logger.warning(
                    f"[{settings.repo}] [{release.version}] Skipping because build failed. (No build/libs)"
                )
                os.chdir(cur_dir)
                return
            files = clone.path("build/libs").iterdir()
            os.chdir(cur_dir)
            for file in files:
                old_path = file.absolute()
                new_path = os.path.join(
                    "builds", repo.owner, repo.name.rsplit("/")[-1], file.name
                )
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                counter = 0
                pause_new_path = new_path
                while os.path.exists(new_path):
                    new_path = pause_new_path.removesuffix(".jar") + f"-{counter}.jar"
                    counter += 1
                os.rename(old_path, new_path)
                release.attached_files.append(
                    (
                        file.name,
                        main_address.removesuffix("/")
                        + "/"
                        + new_path.removeprefix("/"),
                    )
                )
            sorted_assets = sorted(
                [
                    asset
                    for asset in release.attached_files
                    if asset[0].endswith(".jar")
                ],
                key=lambda f: len(f[0]),
                reverse=True,
            )
            if not sorted_assets:
                logger.warning(
                    f"[{settings.repo}] [{release.version}] Skipping, Build seems to have failed."
                )
                return
            jar_path = sorted_assets[0][1].removeprefix(
                main_address.removesuffix("/") + "/"
            )
    else:
        if not release.attached_files:
            logger.warning(
                f"[{settings.repo}] [{release.version}] Skipping because release doesn't have any assets."
            )
            return
        logger.info(
            f"[{settings.repo}] [{release.version}] Downloading release build..."
        )
        sorted_assets = sorted(
            [asset for asset in release.attached_files if asset[0].endswith(".jar")],
            key=lambda f: len(f[0]),
        )
        try:
            jar_path = await download_jar(
                session, sorted_assets[0][1], sorted_assets[0][0]
            )
        except TimeoutError:
            logger.error(
                f"[{settings.repo}] [{release.version}] Download timed out: {sorted_assets[0][1]}"
            )
            return
    return jar_path


def get_from_release(
    jar_path: str,
    settings: datacls.ModSettings,
    repo: datacls.Repo,
    release: datacls.Release,
) -> Optional[datacls.Mod]:
    logger.info(f"[{settings.repo}] [{release.version}] Reading jar...")
    with UnzippedJar(jar_path) as jar:
        mod: Optional[datacls.Mod] = None
        if jar["fabric.mod.json"].exists():
            with jar.open("fabric.mod.json") as f:
                json_content = f.read()
                json_data = json.loads(json_content)
            mod = parsers.parse_fabric_mod_json(settings, repo, json_data, release)
        elif jar["quilt.mod.json"].exists():
            with jar.open("quilt.mod.json") as f:
                json_content = f.read()
                json_data = json.loads(json_content)
            mod = parsers.parse_quilt_mod_json(settings, repo, json_data, release)
        else:
            logger.warning(
                f"[{settings.repo}] [{release.version}] Skipping because it doesn't have a parsable config file."
            )
            return

    if release.version == "dev":
        mod.version = "dev"

    if release.version != mod.version:
        logger.warning(
            f"[{settings.repo}] [{release.version}] The relase tag ({release.tag}) doesn't match the mod version ({mod.version})! Report to the mod author: {mod.ext.owner}"
        )
        logger.info(f"Using the mod version ({mod.version}) as version.")
    return mod


async def get_jars_from_releases(
    main_address: str,
    settings: datacls.ModSettings,
    repo: datacls.Repo,
    releases: list[datacls.Release],
) -> list[tuple[datacls.Release, str]]:
    async with asyncio.TaskGroup() as tg:
        async with aiohttp.ClientSession() as session:
            for release in releases:
                tasks = [
                    tg.create_task(
                        get_repo_jarpath(session, main_address, settings, repo, release)
                    )
                ]
                results = await asyncio.gather(*tasks)
                return [(release, result) for result in results if result]


def get_meta_from_releases(
    jarpaths: list[tuple[datacls.Release, str]],
    settings: datacls.ModSettings,
    repo: datacls.Repo,
) -> list[datacls.Mod]:
    for release, jar_path in jarpaths:
        version = get_from_release(jar_path, settings, repo, release)
        if version:
            yield version


def filter_versions(
    versions: list[datacls.Mod], settings: datacls.ModSettings
) -> list[datacls.Mod]:
    added_versions = []
    for version in versions:
        if version.version not in added_versions:
            added_versions.append(version.version)
        else:
            logger.warning(
                f"[{settings.repo}] Skipping duplicate {version.version} because it has duplicate versions."
            )
            continue
    versions_sorted = [
        version
        for version in sorted(
            versions,
            key=lambda version: (
                not version.ext.prerelease,
                version.ext.published_at,
            ),
            reverse=True,
        )
    ]

    return versions_sorted


async def get_mod(main_address: str, settings: datacls.ModSettings) -> datacls.Mod:
    logger.info(f"[{settings.repo}] Loading Metadata...")
    provider = providers.map[settings.provider]

    repo = provider.get_repo(settings)
    releases = provider.get_releases(settings, repo)
    if settings.dev_builds == True:
        releases.append(provider.get_latest_commit_as_release(settings, repo))
    if not releases:
        logger.warning(
            f"[{settings.repo}] Skipping because it doesn't have any releases."
        )
        return None
    jarpaths = await get_jars_from_releases(main_address, settings, repo, releases)
    versions_unfiltered = get_meta_from_releases(jarpaths, settings, repo)
    filtered_versions = filter_versions(versions_unfiltered, settings)

    versions = list(filtered_versions)

    if not versions:
        logger.warning(
            f"[{settings.repo}] Skipping because it doesn't have any versions."
        )
        return None

    logger.info(f"[{settings.repo}] Finalizing...")

    mod = versions[0]
    mod.ext.alt_versions = versions[1:]
    logger.success(f"[{settings.repo}] Mod loaded.")
    return mod


async def generate_repo(setts):
    logger.info("Loading Mods...")
    mods = [
        await get_mod(setts["address"], datacls.ModSettings.from_dict(mod))
        for mod in setts["mods"]
    ]
    mods = [mod for mod in mods if mod]

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
    repo_map = {}
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
            logger.warning(
                f"[{repo_address}] Skipping because it doesn't have a rootId."
            )
            continue
        repo_id = res["rootId"]
        if not repo_id:
            logger.warning(f"[{repo_address}] Skipping because rootId is empty.")
            continue
        if "mods" not in res:
            logger.warning(f"[{repo_id}] Skipping because it doesn't have mods.")
            continue
        repo_map[repo_id] = repo_address
        repo_results[repo_id] = res["mods"]

    repo_results = {
        k: v
        for k, v in sorted(
            repo_results.items(), key=lambda item: len(item[1]), reverse=True
        )
    }

    for repo_id, repo_mods in repo_results.items():
        logger.info(f"[{repo_id}] Processing mods...")
        for mod in repo_mods:
            if "id" not in mod:
                logger.warning(
                    f"[{repo_id}] Skipping MOD because mod doesn't have an id."
                )
                continue
            if mod["id"] not in mods:
                mods[mod["id"]] = []
            mods[mod["id"]].append(repo_id)

    logger.info("Generating output content...")

    output_content = {
        "mods": mods,
        "repos": repo_map,
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


async def main():
    start = time.time()
    logger.info("Reading config...")
    with open("settings.json", "r", encoding="utf-8") as f:
        setts = json.load(f)
    await generate_repo(setts)
    generate_repo_mapping(setts["repos"])
    logger.success(f"Finished. Took {time.time() - start:.2f}s.")


if __name__ == "__main__":
    asyncio.run(main())
