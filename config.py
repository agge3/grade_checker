"""Loading and validation for milestone grading configuration."""

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, TypedDict, cast
import json


class OptionsConfig(TypedDict):
    """Describe build and output settings from a milestone configuration."""

    os: str
    build: bool
    check_build: bool
    output: bool
    copy: bool


class GradingConfig(TypedDict, total=False):
    """Describe point categories used by the grading workflow."""

    points: int | float
    headers: int | float
    methods: int | float
    build: int | float
    extra_credit: int | float
    total: int | float


class ExtraCreditConfig(TypedDict):
    """Describe optional extra-credit checks."""

    enabled: bool
    args: list[str]


class FetchConfig(TypedDict):
    """Describe repository-fetching behavior."""

    clear: bool


class SubmissionConfig(TypedDict, total=False):
    """Describe files expected in a student submission."""

    required_files: list[str]
    optional_files: list[str]


MethodDefinition = TypedDict(
    "MethodDefinition",
    {"return": str, "params": list[str] | None},
)
MethodsConfig = dict[str, dict[str, MethodDefinition]]


class ConfigData(TypedDict):
    """Describe the complete milestone JSON structure."""

    milestone: str
    prof: str
    org: str
    clone: bool
    glob: str
    usernames_file: str
    classes: list[str]
    methods: MethodsConfig
    options: OptionsConfig
    grading: GradingConfig
    extra_credit: ExtraCreditConfig
    fetch: FetchConfig
    files: list[str]
    submission: SubmissionConfig


ConfigValue = Any


class Config(Mapping[str, ConfigValue]):
    """Represent one validated milestone configuration.

    :param values: The configuration values loaded from a milestone JSON file.
    """

    def __init__(self, values: ConfigData) -> None:
        """Create a configuration object from validated values.

        :param values: The milestone settings to expose through the mapping
            interface.
        """
        self._values = dict(values)

    @property
    def data(self) -> ConfigData:
        """Return the typed configuration data.

        :return: The validated configuration using the declared ``ConfigData``
            structure.
        """
        return cast(ConfigData, self._values)

    def __getitem__(self, key: str) -> ConfigValue:
        """Return a configuration value by key.

        :param key: The top-level configuration key to retrieve.
        :return: The value associated with ``key``.
        :raises KeyError: If ``key`` is not present.
        """
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate over the top-level configuration keys.

        :return: An iterator over configuration key names.
        """
        return iter(self._values)

    def __len__(self) -> int:
        """Return the number of top-level configuration values.

        :return: The number of stored configuration keys.
        """
        return len(self._values)

    def as_dict(self) -> dict[str, ConfigValue]:
        """Return a shallow dictionary copy of the configuration.

        :return: A dictionary containing the top-level configuration values.
        """
        return dict(self._values)


def _validate(values: Mapping[str, ConfigValue]) -> None:
    """Validate the structure required by the grading workflow.

    :param values: Configuration values to validate.
    :raises KeyError: If a required setting is missing.
    :raises TypeError: If a setting has an incompatible structure.
    """
    required_keys = {
        "milestone", "classes", "methods", "options", "grading",
        "extra_credit", "files", "prof", "org", "clone", "glob",
    }
    missing = required_keys - values.keys()
    if missing:
        raise KeyError(f"Missing required key(s): {', '.join(sorted(missing))}")

    options = values["options"]
    if not isinstance(options, Mapping):
        raise TypeError("Options should be a mapping")
    for key in ("os", "build", "output"):
        if key not in options:
            raise KeyError(f"Missing option: {key}")

    grading = values["grading"]
    if not isinstance(grading, Mapping):
        raise TypeError("Grading should be a mapping")
    if "points" not in grading:
        raise KeyError("Missing grading key: points")

    extra_credit = values["extra_credit"]
    if not isinstance(extra_credit, Mapping):
        raise TypeError("Extra credit should be a mapping")
    for key in ("enabled", "args"):
        if key not in extra_credit:
            raise KeyError(f"Missing extra credit key: {key}")

    if not isinstance(values["files"], list):
        raise TypeError("Files should be a list")
    if not isinstance(values["classes"], list):
        raise TypeError("Classes should be a list")

    submission = values.get("submission")
    if submission is not None:
        if not isinstance(submission, Mapping):
            raise TypeError("Submission should be a mapping")
        for key in ("required_files", "optional_files"):
            if key in submission and not isinstance(submission[key], list):
                raise TypeError(f"Submission '{key}' should be a list")

    methods = values["methods"]
    if not isinstance(methods, Mapping):
        raise TypeError("Methods should be a mapping of classes to methods")
    for clazz, class_methods in methods.items():
        if not isinstance(class_methods, Mapping):
            raise TypeError(f"Methods for class '{clazz}' should be a mapping")
        for method_name, definition in class_methods.items():
            if not isinstance(definition, Mapping):
                raise TypeError(f"Definition for method '{method_name}' should be a mapping")
            for key in ("return", "params"):
                if key not in definition:
                    raise KeyError(
                        f"Method '{method_name}' in class '{clazz}' missing '{key}' key"
                    )


def load_config(milestone: str, config_path: Path | None = None) -> Config:
    """Load and validate a milestone configuration.

    :param milestone: The configuration name, such as ``milestone2-hugh``.
    :param config_path: Optional explicit path to a JSON configuration file.
    :return: A configuration object that can be passed to app components.
    :raises FileNotFoundError: If the configuration file does not exist.
    :raises ValueError: If the file is not valid JSON.
    :raises KeyError: If required settings are missing.
    :raises TypeError: If settings have invalid types.
    """
    path = config_path or (
        Path(__file__).resolve().parent / "milestones" / f"_{milestone}.json"
    )
    try:
        with path.open("r", encoding="utf-8") as file:
            values = json.load(file)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Configuration file '{path}' was not found.") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Configuration file '{path}' is not valid JSON.") from error

    if not isinstance(values, dict):
        raise TypeError("The top-level configuration must be a JSON object")
    _validate(values)
    return Config(cast(ConfigData, values))


def print_config(values: Config) -> None:
    """Print a human-readable representation of a configuration.

    :param values: The configuration object to display.
    """
    print(f"Milestone: {values.get('milestone', '')}")
    print(f"\tProfessor: {values.get('prof', '')}")
    print(f"\tClasses: {values.get('classes', [])}")
    print("\tMethods:")
    for clazz, class_methods in values.get("methods", {}).items():
        print(f"\t\t{clazz}:")
        for method_name, definition in class_methods.items():
            print(
                f"\t\t\t{method_name}: returns {definition.get('return', '')}, "
                f"parameters: {definition.get('params', [])}"
            )

    options = values.get("options", {})
    print("\tOptions:")
    print(f"\t\tOS: {options.get('os', 'nix')}")
    print(f"\t\tBuild: {options.get('build', False)}")
    print(f"\t\tOutput: {options.get('output', False)}")
    print(f"\tGrading points: {values.get('grading', {}).get('points', '')}")
    print(f"\tExtra credit: {values.get('extra_credit', {})}")
    print(f"\tFiles: {values.get('files', [])}")


if __name__ == "__main__":
    print_config(load_config("milestone1-hugh"))
