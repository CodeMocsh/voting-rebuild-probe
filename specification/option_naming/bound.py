import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from seams import Option, OptionStore, RecordOptionNamesInput, RecordOptionNamesOut, Seams
from vote.option_names import read_option_names


class InMemoryOptionStore:
    def __init__(self) -> None:
        self.rows: dict[str, Option] = {}

    def seed(self, rows: dict[str, Option]) -> None:
        self.rows = dict(rows)

    def read(self) -> dict[str, Option]:
        return dict(self.rows)


class RecordOptionNames:
    def __init__(self, option_store: OptionStore) -> None:
        self.option_store = option_store

    def __call__(self, given: RecordOptionNamesInput) -> RecordOptionNamesOut:
        environ = {
            variable: value
            for variable, value in (("OPTION_A", given.option_a), ("OPTION_B", given.option_b))
            if value is not None
        }
        names = read_option_names(environ)
        self.option_store.seed(
            {
                "a": Option(id="a", code="a", name=names.option_a),
                "b": Option(id="b", code="b", name=names.option_b),
            }
        )
        return RecordOptionNamesOut()


def seams() -> Seams:
    option_store = InMemoryOptionStore()
    store = option_store
    return Seams(
        reset=lambda: store.seed({}),
        option_store=option_store,
        record_option_names=RecordOptionNames(option_store),
    )
