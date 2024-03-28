# CRM-1-Autorepo

[![Upadate Repo](https://github.com/J0J0HA/CRM-1-Autorepo/actions/workflows/update-repo.yml/badge.svg)](https://github.com/J0J0HA/CRM-1-Autorepo/actions/workflows/update-repo.yml)

## Links

This CRM-1 repository has a hjson and a json build.

- [HJSON](https://crm-repo.jojojux.de/repo.hjson)
- [JSON](https://crm-repo.jojojux.de/repo.json)

## Description

This is a CRM-1 repo updating its contents automatically from GitHub.

## ``settings.json``-Config

For each mod in the ``settings.json``-file, the following attributes are required:

- ``provider``*: The git provider (e.g. ``github``). Currently, only GitHub is supported.
- ``repo``*: The repository name (e.g. ``J0J0HA/CRM-1-Autorepo``).
- ``type``*: The type of the mod (e.g. ``fabric``). Currently, only ``fabric`` is supported.
- ``folder``: The folder in the repository where the mod (the ``src``-folder) is located. If not specified, the root folder is used.
- ``id``: The mod ID (e.g. ``crm-1``). If not specified, the repository name is used (e.g. ``io.github.j0j0ha.CRM-1-Autorepo``).
- ``tag``: The tag of the release to use. If not specified, the latest release is used.
- ``deps``: Additional dependencies of the mod that are not detected by Autorepo. Each dependency has the following attributes:
  - ``id``*: The ID of the dependency.
  - ``version``*: The version of the dependency.
  - ``source``*: The source repo of the dependency.

\* = Required

## ``settings.json``-Example

```json
{
  "mods": [
    {
      "provider": "github",
      "repo": "J0J0HA/CRM-1-Autorepo",
      "type": "fabric",
      "folder": "/",
      "id": "io.github.j0j0ha.CRM-1-Autorepo",
      "tag": "v1.0.0"
    }
  ],
  "rootId": "de.jojojux.crm-repo"
}
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
