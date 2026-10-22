from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class OptionNames:
    option_a: str
    option_b: str


def read_option_names(environ: Mapping[str, str]) -> OptionNames:
    return OptionNames(
        option_a=environ.get("OPTION_A", "Cats"),
        option_b=environ.get("OPTION_B", "Dogs"),
    )
