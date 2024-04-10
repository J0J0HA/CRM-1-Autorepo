import json
import os
import platform
import shutil
import subprocess
import sys
import time
from typing import Optional

import hjson
import requests
from crm1.spec import RMod
from loguru import logger

from utils import ClonedRepo, UnzippedJar, datacls, download_jar
from utils import parser as parsers
from utils import provider as providers

is_windows = platform.system() == "Windows"

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
    level="DEBUG",
    colorize=False,
)


def get_repo_jarpath(
    suffix_priority: list[str],
    main_address: str,
    settings: datacls.ModSettings,
    repo: datacls.Repo,
    release: datacls.Release,
) -> Optional[str]:

    def get_prio(name: str):
        for prio, end in suffix_priority:
            if name.endswith(end):
                return prio
        return len(suffix_priority)

    if not release.is_prebuilt:
        logger.info(f"[{settings.repo}] [{release.version}] Cloning repository...")
        with ClonedRepo(
            repo.git_url,
            ref=release.tag,
            sub=(repo.owner, repo.name.rsplit("/")[-1], release.version, "build"),
        ) as clone:
            logger.info(f"[{settings.repo}] [{release.version}] Building jar...")
            run = (
                ("cmd", "/c", "gradle", "build") if is_windows else ("gradle", "build")
            )
            proc = subprocess.Popen(
                run, cwd=clone.dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            proc.wait()
            ret_val = proc.returncode
            if ret_val != 0:
                logger.warning(
                    f"[{settings.repo}] [{release.version}] Skipping because build failed. (Invalid return value {ret_val})"
                )
                return
            if not clone.path("build/libs").exists():
                logger.warning(
                    f"[{settings.repo}] [{release.version}] Skipping because build failed. (No build/libs)"
                )
                return
            files = clone.path("build/libs").iterdir()
            assets = []
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
                shutil.copy(old_path, new_path)
                assets.append(
                    (
                        file.name,
                        main_address.removesuffix("/")
                        + "/"
                        + new_path.removeprefix("/"),
                    )
                )
            release.attached_files = sorted(
                [asset for asset in assets if asset[0].endswith(".jar")],
                key=lambda f: (get_prio(f[0]), len(f[0])),
            )
            if not release.attached_files:
                logger.warning(
                    f"[{settings.repo}] [{release.version}] Skipping, Build seems to have failed."
                )
                return
            jar_path = os.path.join(
                clone.path("build/libs"), release.attached_files[0][0]
            )
            logger.success(f"[{settings.repo}] [{release.version}] Build successful.")
    else:
        if not release.attached_files:
            logger.warning(
                f"[{settings.repo}] [{release.version}] Skipping because release doesn't have any assets."
            )
            return
        logger.info(
            f"[{settings.repo}] [{release.version}] Downloading release build..."
        )
        release.attached_files = sorted(
            [asset for asset in release.attached_files if asset[0].endswith(".jar")],
            key=lambda f: len(f[0]),
        )
        try:
            jar_path = download_jar(
                release.attached_files[0][1],
                release.attached_files[0][0],
                sub=(
                    repo.owner,
                    repo.name.rsplit("/")[-1],
                    release.version,
                    "download",
                ),
            )
        except TimeoutError:
            logger.error(
                f"[{settings.repo}] [{release.version}] Download timed out: {release.attached_files[0][1]}"
            )
            return
        logger.info(f"[{settings.repo}] [{release.version}] Download successful.")
    return jar_path


def get_from_release(
    jar_path: str,
    settings: datacls.ModSettings,
    repo: datacls.Repo,
    release: datacls.Release,
) -> Optional[RMod]:
    logger.info(f"[{settings.repo}] [{release.version}] Reading jar...")
    with UnzippedJar(
        jar_path,
        sub=(repo.owner, repo.name.rsplit("/")[-1], release.version, "unzipped"),
    ) as jar:
        mod: Optional[RMod] = None
        if jar["fabric.mod.json"].exists():
            with jar.open("fabric.mod.json", "r", encoding="utf-8") as f:
                json_content = f.read()
                json_data = json.loads(json_content)
            mod = parsers.parse_fabric_mod_json(settings, repo, json_data, release)
        elif jar["quilt.mod.json"].exists():
            with jar.open("quilt.mod.json", "r", encoding="utf-8") as f:
                json_content = f.read()
                json_data = json.loads(json_content)
            mod = parsers.parse_quilt_mod_json(settings, repo, json_data, release)
        else:
            logger.warning(
                f"[{settings.repo}] [{release.version}] Skipping because it doesn't have a parsable config file."
            )
            return

    if not release.is_prebuilt:
        mod.version = release.version

    if release.version != mod.version:
        logger.warning(
            f"[{settings.repo}] [{release.version}] The relase tag ({release.tag}) doesn't match the mod version ({mod.version})! Report to the mod author: {mod.ext.owner}"
        )
        logger.info(f"Using the mod version ({mod.version}) as version.")

    if "$" in mod.version or "$" in mod.ext.modid or "$" in mod.id:
        logger.warning(
            f"[{settings.repo}] [{release.version}] Skipping because it has invalid characters in the version or modid."
        )
        return
    logger.info(f"[{settings.repo}] [{release.version}] Jar read.")
    return mod


def get_jars_from_releases(
    suffix_priority: list[str],
    main_address: str,
    settings: datacls.ModSettings,
    repo: datacls.Repo,
    releases: list[datacls.Release],
) -> list[tuple[datacls.Release, str]]:
    return [
        (release, result)
        for release, result in zip(
            releases,
            [
                get_repo_jarpath(suffix_priority, main_address, settings, repo, release)
                for release in releases
            ],
        )
    ]


def get_meta_from_releases(
    jarpaths: list[tuple[datacls.Release, str]],
    settings: datacls.ModSettings,
    repo: datacls.Repo,
) -> list[RMod]:

    return [
        get_from_release(jar_path, settings, repo, release)
        for release, jar_path in jarpaths
        if jar_path is not None
    ]


def filter_versions(versions: list[RMod], settings: datacls.ModSettings) -> list[RMod]:
    """

    :param versions: list[RMod]:
    :param settings: datacls.ModSettings:
    :param versions: list[RMod]:
    :param settings: datacls.ModSettings:

    """
    added_versions: list[RMod] = []
    for version in versions:
        if not version:
            continue
        if version.version not in added_versions:
            added_versions.append(version)
        else:
            logger.warning(
                f"[{settings.repo}] Skipping duplicate {version.version} because it has duplicate versions."
            )
    versions_sorted: list[RMod] = sorted(
        added_versions,
        key=lambda version: (
            not version.ext.prerelease,
            version.ext.published_at,
        ),
        reverse=True,
    )

    return versions_sorted


def get_mod(
    suffix_priority: list[str], main_address: str, settings: datacls.ModSettings
) -> RMod:
    logger.info(f"[{settings.repo}] Loading Metadata...")
    provider = providers.map[settings.provider]

    repo = provider.get_repo(settings)
    releases = provider.get_releases(settings, repo)
    logger.success(f"[{settings.repo}] Metadata loaded.")
    if settings.dev_builds == True:
        releases.append(provider.get_latest_commit_as_release(settings, repo))
    if not releases:
        logger.warning(
            f"[{settings.repo}] Skipping because it doesn't have any releases."
        )
        return None
    jarpaths = get_jars_from_releases(
        suffix_priority, main_address, settings, repo, releases
    )
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


def generate_repo(setts):
    logger.info("Loading Mods...")
    mods = [
        mod
        for mod in [
            get_mod(
                sorted(
                    enumerate(setts["suffixPrios"]),
                    key=lambda x: len(x[1]),
                    reverse=True,
                ),
                setts["address"],
                datacls.ModSettings.from_dict(mod),
            )
            for mod in setts["mods"]
        ]
        if mod
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
    """

    :param repos:

    """
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
