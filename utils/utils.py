import re
import shutil
import tempfile
from git import Repo
import pathlib


class TempDir:
    def __init__(self):
        self.dir = pathlib.Path(tempfile.mkdtemp()).absolute()

    def __enter__(self):
        return self.dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            shutil.rmtree(self.dir)
        except PermissionError:
            pass
        except FileNotFoundError:
            pass


class ClonedRepo(TempDir):
    def __init__(self, git_url, html_url=None):
        super().__init__()
        self.repo = Repo.clone_from(git_url, self.dir)
        self.html_url = html_url or git_url.removesuffix(".git")

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
