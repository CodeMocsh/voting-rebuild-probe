from html.parser import HTMLParser
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
OWN_STYLESHEET = {
    "vote/look.html": "static/stylesheets/style.css",
    "result/look.html": "views/stylesheets/style.css",
}


class LookCheckFailed(Exception):
    pass


class StylesheetLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "link" and "stylesheet" in (attributes.get("rel") or "").split():
            self.links.append(attributes.get("href"))


def main():
    for page, own in OWN_STYLESHEET.items():
        parser = StylesheetLinks()
        parser.feed((REPOSITORY / page).read_text())
        if parser.links != [own]:
            raise LookCheckFailed(f"{page} links {parser.links}, expected only [{own!r}]")
        if not (REPOSITORY / page).parent.joinpath(own).is_file():
            raise LookCheckFailed(f"{page} links {own}, which does not exist")
        print(f"{page} links only {own}")


if __name__ == "__main__":
    main()
