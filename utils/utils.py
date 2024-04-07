import os
import pathlib
import re
import shutil
import tempfile

import requests
from git import Repo


class TempDirProvider:
    def __init__(self):
        # self.parent = tempfile.mkdtemp()
        # self.parent = os.path.join(tempfile.gettempdir(), "autorepo")
        self.parent = os.path.join(os.getcwd(), ".cache")

    def get_temp_dir(self, *sub):
        path = os.path.join(self.parent, *sub)
        os.makedirs(path, exist_ok=True)
        # return tempfile.mkdtemp(dir=path)
        return pathlib.Path(path)
    
    def get_path_nc(self, *sub):
        return os.path.join(self.parent, *sub)

    def has_temp_dir(self, *sub):
        return os.path.exists(os.path.join(self.parent, *sub))

    def delete(self):
        # shutil.rmtree(self.parent, ignore_errors=True)
        pass # Don't delete the parent directory

    def __del__(self):
        self.delete()


TMP_DIRS = TempDirProvider()


class TempDir:
    """ """

    def __init__(self, sub: tuple[str] = (), create=True):
        if create:
            path = TMP_DIRS.get_temp_dir(*sub)
        else:
            path = TMP_DIRS.get_path_nc(*sub)
        self.dir = pathlib.Path(path).absolute()
        
    def create(self):
        os.makedirs(self.dir, exist_ok=True)

    def __enter__(self):
        return self.dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ """
        pass

    def delete(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class ClonedRepo(TempDir):
    """ """

    def __init__(self, git_url, html_url=None, ref=None, sub: tuple[str] = ()):
        super().__init__(sub=sub, create=False)
        if not os.path.exists(self.dir):
            self.create()
            try:
                self.repo = Repo.clone_from(git_url, self.dir)
            except Exception as e:
                self.delete()
                raise e
        else:
            self.repo = Repo(self.dir)
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

        :param file: param *args:
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

    def __init__(self, jar_path, sub: tuple[str] = ()):
        super().__init__(sub=sub, create=False)
        if not os.path.exists(self.dir):
            self.create()
            try:
                shutil.unpack_archive(jar_path, self.dir, format="zip")
            except Exception as e:
                self.delete()
                raise e

    def path(self, file) -> pathlib.Path:
        """

        :param file:

        """
        return self.dir / file

    def open(self, file, action, **kwargs) -> open:
        """

        :param file: param *args:
        :param action: like "r" or "w", gets passed to open()
        :param **kwargs:

        """
        return open(self.path(file), action, **kwargs)

    def __getitem__(self, file) -> pathlib.Path:
        return self.path(file)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)


def download_jar(url, name="download.jar", sub: tuple[str] = ()):
    if TMP_DIRS.has_temp_dir(*sub):
        return TMP_DIRS.get_temp_dir(*sub) / name
    path = TMP_DIRS.get_temp_dir(*sub) / name
    try:
        with open(path, "wb") as f:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except TimeoutError:
        raise TimeoutError(f"Download timed out: {url}") from None
    except Exception as e:
        shutil.rmtree(path.parent, ignore_errors=True)
        raise e
    return path


def replace_vars(text, vars):
    """

    :param text: param vars:
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
