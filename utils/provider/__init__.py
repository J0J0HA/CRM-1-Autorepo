from . import forgejo
from . import github
from .. import data as datacls


class _ProviderTyping:
    """ """
    async def get_repo(self, settings: datacls.ModSettings) -> datacls.Repo:
        # This is only a type hint. look in the forgejo.py and github.py for the actual implementation
        raise NotImplementedError

    async def get_releases(
        self, settings: datacls.ModSettings, repo: datacls.Repo
    ) -> list[datacls.Release]:
        # This is only a type hint. look in the forgejo.py and github.py for the actual implementation
        raise NotImplementedError

    async def get_latest_commit_as_release(
        self, settings: datacls.ModSettings, repo: datacls.Repo
    ) -> datacls.Release:
        # This is only a type hint. look in the forgejo.py and github.py for the actual implementation
        raise NotImplementedError


map: dict[str, _ProviderTyping] = {
    "github": github,
    "codeberg": forgejo,
    "forgejo": forgejo,
}
