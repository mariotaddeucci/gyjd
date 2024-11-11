import os
import tomllib
from dataclasses import fields, is_dataclass
from datetime import date
from functools import cache
from typing import Any, Type, TypeVar

T = TypeVar("T")


def cast_value(value: Any, expected_type: Type) -> Any:
    if isinstance(value, str) and value.startswith("$Env:"):
        env_part = value.removeprefix("$Env:")

        if "|" in env_part:
            env_var_name, default_value = env_part.split("|", 1)
        else:
            env_var_name, default_value = env_part, None

        value = os.getenv(env_var_name, default_value)

        if value is None:
            raise ValueError(f"Environment variable '{env_var_name}' is not set and no default value was provided")

    if isinstance(value, expected_type):
        return value

    try:
        if expected_type is date:
            return date.fromisoformat(value)
        elif expected_type is bool:
            if isinstance(value, str) and value.lower() in {"true", "false"}:
                return value.lower() == "true"
            return bool(value)
        return expected_type(value)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot cast value '{value}' of type '{type(value).__name__}' to '{expected_type}'")


def load_data_to_dataclass(data: dict, dataclass_type: type[T]) -> T:
    field_values = {}

    for field_info in fields(dataclass_type):
        field_name = field_info.name
        field_type = field_info.type
        value = data.get(field_name)

        if value is not None:
            if is_dataclass(field_type):
                field_values[field_name] = load_data_to_dataclass(value, field_type)
            else:
                field_values[field_name] = cast_value(value, field_type)

    return dataclass_type(**field_values)


@cache
def load_file(filepath: str) -> dict:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Config file '{filepath}' not found")

    with open(filepath, "rb") as file:
        data = tomllib.load(file)

    return data


def load_config_from_toml_file(filepath: str, subtree: list[str] | str | None = None) -> dict:
    if subtree is not None:
        if isinstance(subtree, str):
            subtree = [subtree]
    else:
        subtree = []

    data = load_file(filepath)

    for item in subtree:
        if item not in data:
            raise KeyError(f"Path '{item}' not found in config file '{filepath}'")
        data = data[item]

    return data


def load_config_file(
    config_type: type[T],
    filepath: str,
    allow_if_file_not_found: bool = False,
    subtree: list[str] | str | None = None,
):
    try:
        data = load_config_from_toml_file(filepath, subtree)
        return load_data_to_dataclass(data, config_type)
    except FileNotFoundError:
        if not allow_if_file_not_found:
            raise
        return config_type()
