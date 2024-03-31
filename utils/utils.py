import pathlib
import re
import shutil
import tempfile

import aiofiles
import aiohttp
import requests
from git import Repo


class TempDir:
    """ """
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
    """ """
    def __init__(self, git_url, html_url=None, ref=None, no_delete=False):
        super().__init__(no_delete=no_delete)
        self.repo = Repo.clone_from(git_url, self.dir)
        self.html_url = html_url or git_url.removesuffix(".git")

        if ref:
            self.repo.git.checkout(ref)

    def path(self, file) -> pathlib.Path:
        """

        :param file: 

        """
        return self.dir / file

    def open(self, file, *args, **kwargs) -> open:
        """

        :param file: 
        :param *args: 
        :param **kwargs: 

        """
        return open(self.path(file), *args, **kwargs)

    def __getitem__(self, file) -> pathlib.Path:
        return self.path(file)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.repo.close()
        super().__exit__(exc_type, exc_val, exc_tb)


class UnzippedJar(TempDir):
    """ """
    def __init__(self, jar_path, no_delete=False):
        super().__init__(no_delete=no_delete)
        shutil.unpack_archive(jar_path, self.dir, format="zip")

    def path(self, file) -> pathlib.Path:
        """

        :param file: 

        """
        return self.dir / file

    def open(self, file, *args, **kwargs) -> open:
        """

        :param file: 
        :param *args: 
        :param **kwargs: 

        """
        return open(self.path(file), *args, **kwargs)

    def __getitem__(self, file) -> pathlib.Path:
        return self.path(file)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)


async def download_jar(session: aiohttp.ClientSession, url, name="download.jar"):
    path = tempfile.mkdtemp() + "/" + name
    try:
        with open(path, "wb") as f:
            async with session.get(url) as response:
                response.raise_for_status()
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
    except TimeoutError:
        raise TimeoutError(f"Download timed out: {url}")
    return path


def replace_vars(text, vars):
    """

    :param text: 
    :param vars: 

    """
    for var in vars:
        text = text.replace("${" + var + "}", vars[var])

    def replace(match):
        """

        :param match: 

        """
        if match.group(1) not in vars:
            return "null"
        return vars[match.group(1)]

    text = re.sub(r"\$\{(\w+?)\}", replace, text)
    text = text.replace('"null"', "null")
    return text
