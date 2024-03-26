# CRM-1-Autorepo

[![Build Repo](https://github.com/J0J0HA/crm-1-git-repo/actions/workflows/build-repo.yml/badge.svg)](https://github.com/J0J0HA/crm-1-git-repo/actions/workflows/build-repo.yml)

## Description

This is a CRM-1 repo updating its contents automatically from GitHub.

## ``settings.json``-Config

For each mod in the ``settings.json``-file, the following attributes are required:

- ``provider``*: The git provider (e.g. ``github``). Currently, only GitHub is supported.
- ``repo``*: The repository name (e.g. ``J0J0HA/crm-1-git-repo``).
- ``type``*: The type of the mod (e.g. ``fabric``). Currently, only ``fabric`` is supported.
- ``folder``: The folder in the repository where the mod (the ``src``-folder) is located. If not specified, the root folder is used.
- ``id``: The mod ID (e.g. ``crm-1``). If not specified, the repository name is used (e.g. ``io.github.j0j0ha.crm-1-git-repo``).
- ``tag``: The tag of the release to use. If not specified, the latest release is used.

\* = Required

## ``settings.json``-Example

```json
{
  "mods": [
    {
      "provider": "github",
      "repo": "J0J0HA/crm-1-git-repo",
      "type": "fabric",
      "folder": "/",
      "id": "io.github.j0j0ha.crm-1-git-repo",
      "tag": "v1.0.0"
    }
  ],
  "rootId": "io.github.j0j0ha.crm-1-git-repo"
}
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
