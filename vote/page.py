import json
from html import escape
from pathlib import Path
from string import Template
from typing import Protocol

BALLOT = Template((Path(__file__).parent / "templates" / "index.html").read_text())


class Labels(Protocol):
    a: str
    b: str


def _tick(options: Labels, vote: str) -> str:
    labels = {"a": options.a, "b": options.b}
    other = {"a": "b", "b": "a"}[vote]
    ticked = json.dumps(f'{escape(labels[vote])} <i class="fa fa-check-circle"></i>')
    return (
        "    <script>\n"
        f'      var vote = "{vote}";\n'
        f"      $(\".{vote}\").prop('disabled', true);\n"
        f'      $(".{vote}").html({ticked});\n'
        f"      $(\".{other}\").css('opacity','0.5');\n"
        "    </script>"
    )


def render(options: Labels, vote: str | None, refusal: str | None, hostname: str) -> str:
    return BALLOT.substitute(
        option_a=escape(options.a),
        option_b=escape(options.b),
        hostname=escape(hostname),
        refusal="" if refusal is None else f'        <div id="refusal">{escape(refusal)}</div>',
        tick="" if vote is None else _tick(options, vote),
    )
