from . import github
from . import forgejo


map = {
    "github": github,
    "codeberg": forgejo,
    "forgejo": forgejo,
}
