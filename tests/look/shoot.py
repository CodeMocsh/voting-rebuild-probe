import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPOSITORY = Path(__file__).resolve().parents[2]
VIEWPORT = {"width": 720, "height": 540}
PAGES = {
    "vote": [
        "ballot", "heading", "option-a", "option-a-hover", "option-b", "option-b-hover",
        "voted-a", "voted-b", "tip", "hostname",
    ],
    "result": [
        "results", "background-split", "score-card", "total-none", "total-one", "total-many",
    ],
}


class LookCheckFailed(Exception):
    pass


def shoot_part(browser, part, expected, out, steps):
    part_dir = (REPOSITORY / part).as_uri() + "/"
    page = browser.new_page(viewport=VIEWPORT)
    broken = []
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(part_dir) else route.abort())
    page.on("requestfailed", lambda request: broken.append(request.url) if request.url.startswith(part_dir) else None)
    page.goto(part_dir + "look.html")
    page.wait_for_load_state("load")
    if broken:
        raise LookCheckFailed(f"{part}/look.html cannot load its own files: {broken}")

    specimens = page.locator("[data-specimen]")
    names = [specimens.nth(i).get_attribute("data-specimen") for i in range(specimens.count())]
    if names != expected:
        raise LookCheckFailed(f"{part}/look.html has specimens {names}, expected {expected}")

    for name in names:
        element = page.locator(f'[data-specimen="{name}"]')
        hover = element.get_attribute("data-state") == "hover"
        said = None
        if hover:
            element.hover()
            if not element.locator("button").evaluate("button => button.matches(':hover')"):
                said = "The pointer is on the frame but not on its button."
        file = f"{part}-{name}.png"
        element.screenshot(path=str(out / file))
        box = element.bounding_box()
        if said is None and (box is None or box["width"] == 0 or box["height"] == 0):
            said = "The specimen has no visible area."
        page.mouse.move(0, 0)
        steps.append({
            "caption": f"{part}: {name}" + (" on hover" if hover else ""),
            "file": file,
            "holds": said is None,
            "said": said,
        })
    page.close()

    shot = sorted(out.glob(f"{part}-*.png"))
    if len(shot) != len(names):
        raise LookCheckFailed(f"{part}: {len(shot)} screenshots for {len(names)} specimens")


def main():
    out = Path(os.environ["TOKIWA_SCREENSHOTS"])
    out.mkdir(parents=True, exist_ok=True)
    steps = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for part, expected in PAGES.items():
            shoot_part(browser, part, expected, out, steps)
        browser.close()
    (out / "steps.json").write_text(json.dumps({"steps": steps}, indent=2))
    failed = [step["caption"] for step in steps if not step["holds"]]
    if failed:
        raise LookCheckFailed(f"Steps that do not hold: {failed}")
    print(f"{len(steps)} specimens, {len(steps)} screenshots in {out}")


if __name__ == "__main__":
    main()
    sys.exit(0)
