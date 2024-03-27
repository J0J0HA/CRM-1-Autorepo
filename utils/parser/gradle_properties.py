def parse_gradle_properties(init_content: str):
    properties = {}

    for line in init_content.splitlines():
        if not line or line.strip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        properties[key.strip()] = value.strip()

    return properties
