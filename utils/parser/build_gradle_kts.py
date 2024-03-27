import re


def parse_build_gradle_kts(init_content: str) -> dict:
    objects = {}
    for obj in init_content.split("object "):
        if not obj:
            continue
        name = obj[: obj.find("{")].strip()
        if name:
            objects[name] = {}
        content = obj[obj.find("{") :]
        content = content[: content.find("}")]
        content = content.removeprefix("{").removesuffix("}")
        for prop in content.split("\n"):
            prop = prop.strip()
            if not prop:
                continue
            key, value = prop.split("=")
            key = key.removeprefix("const ").removeprefix("val ").strip()
            value = value.strip().removeprefix('"').removesuffix('"')
            objects[name][key] = value

    what_to_expand = [
        match.group(1) for match in re.finditer(r"expand\((.+?)\)", init_content)
    ]

    properties = {}

    for val in what_to_expand:
        content = init_content[init_content.find(f"val {val} = mapOf(") :]
        content = content[: content.find(")")]
        content = content.removeprefix(f"val {val} = mapOf(").removesuffix(")")
        content = content.split(",")
        content = [x.strip() for x in content]
        for prop in content:
            if not prop:
                continue
            key, value = prop.split(" to ")
            key = key.removeprefix('"').removesuffix('"')
            object, value = value.split(".", 1)
            if object not in objects:
                continue
            if value in objects[object]:
                properties[key] = objects[object][value]
    return properties
