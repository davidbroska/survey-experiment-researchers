"""Stage the public SCORE site and preserved TESS site from explicit file lists."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = (
    "index.html", "articles.csv", "journals.csv", "journal_audit.csv",
    "sample_validation.json", "access.csv", "coverage.csv", "manual_downloads.csv",
    "independent_review.csv", "predictions_original.csv", "predictions_revised.csv",
    "evaluation.json", "prompt_original.md", "prompt_revised.md", "prompt_current.md",
    "prompt_freeze.json", "protocol.md", "report.md", "ra_verification.md",
)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        self.targets.extend(value for key, value in attrs if key in ("href", "src") and value)


def check_links(site):
    count = 0
    for path in site.rglob("*.html"):
        links = Links()
        links.feed(path.read_text())
        for target in links.targets:
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            destination = (path.parent / unquote(url.path)).resolve()
            if not destination.is_relative_to(site.resolve()) or not destination.is_file():
                raise ValueError(f"Broken or escaping link: {path}: {target}")
            count += 1
    return count


def redirect(path, target):
    path.write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
                    f'<meta http-equiv="refresh" content="0;url={target}">'
                    f'<title>Researcher recruitment</title><a href="{target}">Open dashboard</a></html>')


def main():
    site = ROOT / "site"
    if site.exists():
        shutil.rmtree(site)
    (site / "score").mkdir(parents=True)
    for name in PUBLIC:
        shutil.copy2(ROOT / "score" / name, site / "score" / name)
    # This is the previously published 258-file website, not the research folder.
    shutil.copytree(ROOT / "archive/tess/site", site / "archive/tess")
    redirect(site / "index.html", "score/index.html")
    for name in ("DASHBOARD_NARROWER.html", "DASHBOARD_COMPLETE.html", "DASHBOARD_ORIGINAL.html", "TOP40.html", "TOP100.html"):
        redirect(site / name, "archive/tess/" + name)
    count = check_links(site)
    print(f"Staged public site; checked {count} local HTML links.")


if __name__ == "__main__":
    main()
