"""Replays a capability's cases through the seams a build bound, and writes what it saw.

Shipped into a capability task's folder as `replay.py`, beside `seams.py`, `cases.json` and the
build's `bound.py`, and run by the host's check from that folder with the standard library alone.
Its one argument is the repository's root, which `bound.py` imports the build's code from.
It judges nothing: for each step it writes what the action sent and every record before and after,
to the file `TOKIWA_RULES` names, and the host evaluates each expectation and rule there. Run with
no such file, it prints how each case ran and writes nothing.

Exits 0 once every case ran, and 1 where the seams cannot be had: `bound.py` is missing, fails to
import, or its `seams()` does not return a whole `Seams`.
"""

import dataclasses
import importlib.util
import json
import os
import signal
import sys
import traceback
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager, nullcontext
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import FrameType, ModuleType
from typing import Any, Final

OBSERVED_AT: Final = "TOKIWA_RULES"
CASES: Final = "cases.json"
STEP_FOR: Final = 30
"""The longest one step may take, in seconds, before it counts as raised."""
LONGEST: Final = 65_536
"""The most characters of one value sent that is kept."""


class Unbound(RuntimeError):
    """The build's seams cannot be had."""


def _module(folder: Path, name: str) -> ModuleType:
    path = folder / f"{name}.py"
    if not path.is_file():
        raise Unbound(f"{name}.py is not in {folder}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Unbound(f"{name}.py cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _named(kind: type) -> dict[str, str]:
    return {one.metadata.get("named", one.name): one.name for one in dataclasses.fields(kind)}


PARSED: Final[dict[str, Callable[[str], Any]]] = {
    "decimal": Decimal,
    "date": date.fromisoformat,
    "datetime": datetime.fromisoformat,
}
"""How a value of each kind the JSON holds as a string is made, by its value type."""


def _value(kind: str, value: Any) -> Any:
    parse = PARSED.get(kind)
    return value if value is None or parse is None else parse(str(value))


def _made(kind: type, kinds: Mapping[str, str], values: Mapping[str, Any]) -> Any:
    named = _named(kind)
    return kind(**{named[key]: _value(kinds.get(key, "text"), one) for key, one in values.items()})


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    return value.isoformat() if isinstance(value, date) else str(value)


def _plain(value: Any) -> Any:
    held = json.loads(json.dumps(value, default=_jsonable))
    return held[:LONGEST] if isinstance(held, str) else held


def _record(kind: type, row: Any) -> dict[str, Any]:
    if (
        not dataclasses.is_dataclass(row)
        or isinstance(row, type)
        or type(row).__name__ != kind.__name__
    ):
        raise TypeError(f"read() gave a {type(row).__name__}, not a {kind.__name__}")
    named = {held: said for said, held in _named(kind).items()}
    return {named[key]: _plain(one) for key, one in dataclasses.asdict(row).items()}


class Replay:
    """The seams of one build, and the module that declares them."""

    def __init__(self, seams: ModuleType, bound: Any) -> None:
        self.seams: ModuleType = seams
        self.bound: Any = bound

    def _store(self, symbol: str) -> tuple[Any, type]:
        attribute, kind = self.seams.STORES[symbol]
        return getattr(self.bound, attribute), getattr(self.seams, kind)

    def seed(self, given: Mapping[str, Mapping[str, Any]]) -> None:
        for symbol, rows in given.items():
            store, kind = self._store(symbol)
            kinds = self.seams.KINDS[symbol]
            store.seed({key: _made(kind, kinds, {**row, "id": key}) for key, row in rows.items()})

    def read(self) -> dict[str, dict[str, Any]]:
        state: dict[str, dict[str, Any]] = {}
        for symbol in self.seams.STORES:
            store, kind = self._store(symbol)
            state[symbol] = {str(key): _record(kind, row) for key, row in store.read().items()}
        return state

    def call(self, action: str, given: Mapping[str, Any]) -> dict[str, Any]:
        attribute, kind = self.seams.ACTIONS[action]
        made = _made(getattr(self.seams, kind), self.seams.INPUTS[action], given)
        sent = getattr(self.bound, attribute)(made)
        if not dataclasses.is_dataclass(sent) or isinstance(sent, type):
            raise TypeError(f"{attribute} returned a {type(sent).__name__}, not its Out")
        return {
            key: _plain(one) for key, one in dataclasses.asdict(sent).items() if one is not None
        }

    def down(self, fault: str | None) -> Any:
        if fault is None:
            return nullcontext()
        return getattr(self.bound.unavailable, self.seams.FAULTS[fault])()


def _bound(folder: Path, root: Path) -> Replay:
    sys.path[:0] = [str(folder), str(root)]
    seams = _module(folder, "seams")
    try:
        made = _module(folder, "bound").seams()
    except Unbound:
        raise
    except Exception as failed:
        raise Unbound(f"bound.seams() raised {type(failed).__name__}: {failed}") from failed
    if type(made).__name__ != "Seams":
        raise Unbound(f"bound.seams() returned a {type(made).__name__}, not a Seams")
    return Replay(seams, made)


def _timed_out(_signal: int, _frame: FrameType | None) -> None:
    raise TimeoutError(f"the step ran longer than {STEP_FOR} seconds")


@contextmanager
def _limited() -> Generator[None]:
    previous = signal.signal(signal.SIGALRM, _timed_out)
    signal.alarm(STEP_FOR)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def _step(replay: Replay, step: Mapping[str, Any]) -> dict[str, Any]:
    with _limited():
        replay.seed(step["given"])
        before = replay.read()
        with replay.down(step["fault"]):
            sent = replay.call(step["action"], step["input"])
        return {"sent": sent, "before": before, "after": replay.read()}


def _raised(failed: BaseException) -> dict[str, Any]:
    said = traceback.format_exception_only(type(failed), failed)[-1].strip()
    return {"raised": said[:LONGEST]}


def _reset(replay: Replay, _step: Mapping[str, Any] | None) -> dict[str, Any]:
    with _limited():
        replay.bound.reset()
    return {}


def _ran(
    run: Callable[[Replay, Mapping[str, Any]], dict[str, Any]], replay: Replay, step: Any
) -> dict[str, Any]:
    """What one step saw, or what it raised: the build's own code runs here, and anything it
    raises is what the host judges the case broken by."""
    try:
        return run(replay, step)
    except Exception as failed:
        return _raised(failed)


def _case(replay: Replay, case: Mapping[str, Any], say: Callable[[str], None]) -> list[Any]:
    reset = _ran(_reset, replay, None)
    seen: list[Any] = [reset] if reset else []
    for step in case["steps"] if not reset else []:
        seen.append(_ran(_step, replay, step))
        if "raised" in seen[-1]:
            break
    raised = [one["raised"] for one in seen if "raised" in one]
    say(f"raised  {case['name']}: {raised[0]}" if raised else f"ran     {case['name']}")
    return seen


def _said(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def _saved(out: str | None, seen: Mapping[str, Any]) -> None:
    if out is not None:
        Path(out).write_text(json.dumps(seen, sort_keys=True))


def main(argv: list[str]) -> int:
    folder = Path(__file__).resolve().parent
    root = Path(argv[0]) if argv else folder
    out = os.environ.get(OBSERVED_AT)
    try:
        replay = _bound(folder, root)
    except Unbound as unbound:
        _saved(out, {"unbound": str(unbound)})
        sys.stdout.write(f"unbound {unbound}\n")
        return 1
    cases = json.loads((folder / CASES).read_text())["cases"]
    observed = {one["key"]: _case(replay, one, _said) for one in cases}
    _saved(out, {"cases": observed})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
