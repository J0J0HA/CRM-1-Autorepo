import re
import shutil
import tempfile
from git import Repo
import pathlib

import requests


class TempDir:
    def __init__(self, no_delete=False):
        self.dir = pathlib.Path(tempfile.mkdtemp()).absolute()
        self.no_delete = no_delete

    def __enter__(self):
        return self.dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.no_delete:
            return
        try:
            shutil.rmtree(self.dir)
        except PermissionError:
            pass
        except FileNotFoundError:
            pass


class ClonedRepo(TempDir):
    def __init__(self, git_url, html_url=None, ref=None, no_delete=False):
        super().__init__(no_delete=no_delete)
        self.repo = Repo.clone_from(git_url, self.dir)
        self.html_url = html_url or git_url.removesuffix(".git")

        if ref:
            self.repo.git.checkout(ref)

    def path(self, file) -> pathlib.Path:
        return self.dir / file

    def open(self, file, *args, **kwargs) -> open:
        return open(self.path(file), *args, **kwargs)

    def __getitem__(self, file) -> pathlib.Path:
        return self.path(file)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.repo.close()
        super().__exit__(exc_type, exc_val, exc_tb)


class UnzippedJar(TempDir):
    def __init__(self, jar_path, no_delete=False):
        super().__init__(no_delete=no_delete)
        shutil.unpack_archive(jar_path, self.dir, format="zip")

    def path(self, file) -> pathlib.Path:
        return self.dir / file

    def open(self, file, *args, **kwargs) -> open:
        return open(self.path(file), *args, **kwargs)

    def __getitem__(self, file) -> pathlib.Path:
        return self.path(file)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)


def download_jar(url, name="download.jar"):
    path = tempfile.mkdtemp() + "/" + name
    try:
        with open(path, "wb") as f:
            with requests.get(url, stream=True, timeout=10) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except TimeoutError:
        raise TimeoutError(f"Download timed out: {url}")
    return path


def replace_vars(text, vars):
    for var in vars:
        text = text.replace("${" + var + "}", vars[var])

    def replace(match):
        if match.group(1) not in vars:
            return "null"
        return vars[match.group(1)]

    text = re.sub(r"\$\{(\w+?)\}", replace, text)
    text = text.replace('"null"', "null")
    return text
