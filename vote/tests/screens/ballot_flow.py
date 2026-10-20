import json
import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Page, Route, sync_playwright
from werkzeug.serving import make_server

from vote.ballot import Options
from vote.votes_queue import MemoryVotesQueue
from vote.web import create_app

VIEWPORT = {"width": 720, "height": 540}
JQUERY = """
window.jQuery = window.$ = function (selector) {
  var found = document.querySelectorAll(selector);
  var each = function (apply) { found.forEach(apply); return chain; };
  var chain = {
    prop: function (name, value) { return each(function (one) { one[name] = value; }); },
    html: function (markup) { return each(function (one) { one.innerHTML = markup; }); },
    css: function (name, value) { return each(function (one) { one.style[name] = value; }); }
  };
  return chain;
};
"""
FONT_AWESOME = '.fa-check-circle:before { content: "\\2714"; }'
STUBS = {
    "https://code.jquery.com/jquery-latest.min.js": ("application/javascript", JQUERY),
    "https://cdnjs.cloudflare.com/ajax/libs/jquery-cookie/1.4.1/jquery.cookie.js": ("application/javascript", ""),
    "https://maxcdn.bootstrapcdn.com/font-awesome/4.4.0/css/font-awesome.min.css": ("text/css", FONT_AWESOME),
    "https://fonts.googleapis.com/css?family=Open+Sans:400,700,600": ("text/css", ""),
}


class Flow:
    def __init__(self, page: Page, queue: MemoryVotesQueue, shots: Path) -> None:
        self.page = page
        self.queue = queue
        self.shots = shots
        self.steps: list[dict] = []

    def step(self, caption: str, act: Callable[[], str | None]) -> None:
        said = act()
        file = f"{len(self.steps) + 1}.png"
        self.page.screenshot(path=str(self.shots / file))
        self.steps.append({"caption": caption, "file": file, "holds": said is None, "said": said})

    def voter_id(self) -> str | None:
        cookies = {one["name"]: one["value"] for one in self.page.context.cookies()}
        return cookies.get("voter_id")

    def disabled(self) -> tuple[bool, bool]:
        return self.page.is_disabled("#a"), self.page.is_disabled("#b")

    def open_ballot(self, base: str) -> str | None:
        status = self.page.goto(base).status
        if status != 200:
            return f"GET / answered {status}"
        if not self.voter_id():
            return "the ballot set no voter_id cookie"
        if self.disabled() != (False, False):
            return "a button is disabled before any vote"
        return None

    def cast(self, button: str, expected: tuple[bool, bool], choice: str) -> str | None:
        with self.page.expect_navigation() as answered:
            self.page.click(button)
        status = answered.value.status
        if status != 200:
            return f"POST / answered {status}"
        if self.disabled() != expected:
            return f"buttons disabled (Cats, Dogs) are {self.disabled()}, not {expected}"
        if self.queue.pending()[-1] != {"voter_id": self.voter_id(), "vote": choice}:
            return f"the last queued vote is {self.queue.pending()[-1]}"
        return None

    def cast_empty(self) -> str | None:
        queued = len(self.queue.pending())
        self.page.eval_on_selector("#a", "button => { button.value = ''; }")
        with self.page.expect_navigation() as answered:
            self.page.click("#a")
        status = answered.value.status
        if status != 400:
            return f"POST / with an empty vote answered {status}"
        if not self.page.is_visible("#refusal"):
            return "the refusal line is not visible"
        if len(self.queue.pending()) != queued:
            return "the empty vote was queued"
        return None


def main() -> int:
    shots = Path(os.environ["TOKIWA_SCREENSHOTS"])
    shots.mkdir(parents=True, exist_ok=True)
    queue = MemoryVotesQueue()
    server = make_server("127.0.0.1", 0, create_app(queue, Options(a="Cats", b="Dogs")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/"
    unexpected: list[str] = []

    def answer(route: Route) -> None:
        url = route.request.url
        if url.startswith(base):
            route.continue_()
        elif url in STUBS:
            kind, body = STUBS[url]
            route.fulfill(status=200, content_type=kind, body=body)
        else:
            unexpected.append(url)
            route.abort()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        page.route("**/*", answer)
        flow = Flow(page, queue, shots)
        try:
            flow.step("Open the ballot", lambda: flow.open_ballot(base))
            flow.step("Vote Cats", lambda: flow.cast("#a", (True, False), "a"))
            flow.step("Change the vote to Dogs", lambda: flow.cast("#b", (False, True), "b"))
            flow.step("Cast an empty vote", flow.cast_empty)
            if unexpected:
                flow.steps[-1].update(holds=False, said=f"the page asked for {unexpected}")
        finally:
            (shots / "steps.json").write_text(json.dumps({"steps": flow.steps}, indent=1))
            browser.close()
            server.shutdown()
    return 0 if all(one["holds"] for one in flow.steps) else 1


if __name__ == "__main__":
    sys.exit(main())
