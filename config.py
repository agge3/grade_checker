import json

# xxx do we want a different format, to decouple from the json?
# Global configuration dictionary.
#_config = {
#    "os": "nix",
#    "class": "",
#    "methods": [
#        {
#            "name": "",
#            "return": "",
#            "parameters": [],
#        }
#    ],
#    "build": False,
#    "output": False,
#    "files": [],
#    "points": "",
#    "extra_credit": {
#        "enabled": True,
#        "args": [],
#    },
#}

# Global configuration dictionary.
_config = {}

def validate():
    """Validates that all necessary keys exist in the _config structure."""
    required_keys = [
        'milestone', 'class', 'methods', 'options', 'grading', 'extra_credit',
        'files', 'prof', 'org', 'clone', 'glob'
    ]

    for key in required_keys:
        if key not in _config:
            raise KeyError(f"Missing required key: {key}")

    # Validate nested keys
    if 'options' in _config:
        option_keys = ['os', 'build', 'output']
        for option_key in option_keys:
            if option_key not in _config['options']:
                raise KeyError(f"Missing option: {option_key}")

    if 'grading' in _config and 'points' not in _config['grading']:
        raise KeyError("Missing grading key: points")

    if 'extra_credit' in _config:
        extra_credit_keys = ['enabled', 'args']
        for extra_key in extra_credit_keys:
            if extra_key not in _config['extra_credit']:
                raise KeyError(f"Missing extra credit key: {extra_key}")

    if 'files' in _config and not isinstance(_config['files'], list):
        raise TypeError("Files should be a list")

def merge(milestone):
    """Merges the milestone configuration into the global _config."""
    global _config  # Ensure the function modifies the global _config.

    # Construct the full path for the milestone.
    print(milestone)
    path = f"milestones/_{milestone}.json"
    print(path)

    # Read JSON config from the milestone path.
    try:
        with open(path, "r") as file:
            cfg = json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Error: The file '{path}' was not found. " + 
            f"Please ensure the path is correct."
        )
    except json.JSONDecodeError:
        raise ValueError(
            f"Error: The file '{path}' is not a valid JSON file. " + 
            f"Please check its contents."
        )

    # xxx do we want a different format, to decouple from the json?
    # Populate the global config map.
    #_config.update({
    #    "milestone": cfg.get("milestone", ""),
    #    "os": cfg.get("os", "nix"),
    #    "class": cfg.get("class", ""),
    #    "methods": [
    #        {
    #            "name": method.get("name", ""),
    #            "return": method.get("return", ""),
    #            "parameters": method.get("parameters", []),
    #        }
    #        for method in cfg.get("methods", [])
    #    ],
    #    "build": cfg.get("build", False),
    #    "output": cfg.get("output", False),
    #    "files": cfg.get("files", []),
    #    "points": cfg["grading"]["points"],
    #    "extra_credit": {
    #        "enabled": cfg.get("extra_credit", {}).get("enabled", True),
    #        "args": cfg.get("extra_credit", {}).get("args", []),
    #    },
    #})

    # Populate the global config map.
    _config.update(cfg)
    validate()



def print_config():
    """Prints the global _config dictionary in a formatted way."""
    print(f"Milestone: {_config.get('milestone', '')}")
    print(f"\tClass: {_config.get('class', '')}")

    print("\tMethods:")
    methods = _config.get("methods", {})
    for method_name, method_details in methods.items():
        return_type = method_details.get("return", "")
        parameters = method_details.get("parameter", [])
        print(f"\t\t{method_name}: returns {return_type}, parameter: {parameters}")

    print("\tOptions:")
    print(f"\t\tOS: {_config.get('options', {}).get('os', 'nix')}")
    print(f"\t\tBuild: {_config.get('options', {}).get('build', False)}")
    print(f"\t\tOutput: {_config.get('options', {}).get('output', False)}")

    print("\tGrading:")
    print(f"\t\tPoints: {_config.get('grading', {}).get('points', '')}")

    print("\tExtra Credit:")
    extra_credit = _config.get("extra_credit", {})
    print(f"\t\tEnabled: {extra_credit.get('enabled', True)}")
    print(f"\t\tArgs: {extra_credit.get('args', [])}")

    print("\tFiles:")
    files = _config.get("files", [])
    for file in files:
        print(f"\t\t{file}")

# Example usage
if __name__ == "__main__":
    merge("milestone1")
    print_config()
    methods_to_strlst()
