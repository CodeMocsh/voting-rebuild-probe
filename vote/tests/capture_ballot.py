import json
import os
import sys
from pathlib import Path

from flask import Flask, render_template
from playwright.sync_api import sync_playwright

VOTE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VOTE.parent))

from vote.option_names import read_option_names

SCREENSHOTS = Path(os.environ["TOKIWA_SCREENSHOTS"])


def render(environ):
    names = read_option_names(environ)
    app = Flask("vote", root_path=str(VOTE))
    with app.test_request_context("/"):
        return render_template(
            "index.html",
            option_a=names.option_a,
            option_b=names.option_b,
            hostname="vote-7d9f",
            vote=None,
        )


def main():
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    page_source = render({"OPTION_A": "Tea", "OPTION_B": "Coffee"})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 720, "height": 540})
        page.set_content(page_source)
        title = page.title()
        buttons = [page.inner_text("#a"), page.inner_text("#b")]
        heading = page.inner_text("h3")
        page.screenshot(path=str(SCREENSHOTS / "1.png"))
        browser.close()
    holds = title == "Tea vs Coffee!" and heading == "Tea vs Coffee!" and buttons == ["Tea", "Coffee"]
    step = {
        "caption": "Ballot with Tea and Coffee",
        "file": "1.png",
        "holds": holds,
        "said": None if holds else f"title {title!r}, heading {heading!r}, buttons {buttons!r}",
    }
    (SCREENSHOTS / "steps.json").write_text(json.dumps({"steps": [step]}))
    sys.exit(0 if holds else 1)


main()
