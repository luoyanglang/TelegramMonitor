import argparse
import os
import re
from pathlib import Path


VERSION_HEADING_RE = re.compile(r"^##\s+\[(?P<version>v?[^\]]+)\](?:\s+-\s+(?P<date>.+))?\s*$")
SECTION_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")
LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")


def normalize_version(version: str) -> str:
    return version.strip().lstrip("v")


def extract_changelog_section(changelog_text: str, version: str) -> str:
    """Extract the matching version section from CHANGELOG.md."""
    wanted_version = normalize_version(version)
    lines = changelog_text.splitlines()
    start = None

    for index, line in enumerate(lines):
        match = VERSION_HEADING_RE.match(line)
        if match and normalize_version(match.group("version")) == wanted_version:
            start = index
            break

    if start is None:
        raise ValueError(f"Version {version} was not found in CHANGELOG.md")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break

    return "\n".join(lines[start:end]).strip()


def extract_highlights(changelog_section: str, limit: int = 4) -> list[str]:
    """Collect the first user-facing changelog bullets for Telegram highlights."""
    sections: dict[str, list[str]] = {
        "added": [],
        "changed": [],
        "fixed": [],
        "security": [],
    }
    active_section = None

    for line in changelog_section.splitlines():
        heading_match = SECTION_HEADING_RE.match(line)
        if heading_match:
            active_section = heading_match.group(1).strip().lower()
            continue

        if active_section not in {"added", "changed", "fixed", "security"}:
            continue

        item_match = LIST_ITEM_RE.match(line)
        if item_match:
            sections[active_section].append(item_match.group(1).strip())

    highlights: list[str] = []
    preferred_slots = (
        ("added", 2),
        ("changed", 1),
        ("fixed", 1),
        ("security", 1),
    )
    for section_name, count in preferred_slots:
        for item in sections[section_name][:count]:
            if item not in highlights:
                highlights.append(item)
            if len(highlights) == limit:
                return highlights

    for section_name in ("added", "changed", "fixed", "security"):
        for item in sections[section_name]:
            if item not in highlights:
                highlights.append(item)
            if len(highlights) == limit:
                return highlights

    return highlights


def build_release_body(
    version: str,
    changelog_section: str,
    repo: str,
    dockerhub_username: str,
    docker_image_name: str,
) -> str:
    highlights = extract_highlights(changelog_section)
    docker_ref = f"{dockerhub_username}/{docker_image_name}:{version}"
    highlight_block = "\n".join(f"- {item}" for item in highlights)
    if not highlight_block:
        highlight_block = "- Review the update notes below for release details."

    return f"""## Telegram Monitor {version}

### Highlights

{highlight_block}

### Update Notes

{changelog_section}

### Downloads

| Type | Details |
|------|---------|
| Docker | `docker pull {docker_ref}` |
| Linux binary | Download `telegram-monitor-linux-x64.tar.gz` |
| Windows binary | Download `telegram-monitor-windows-x64.zip` |
| Source code | Download the GitHub source archive |

### Quick Start

```bash
wget https://raw.githubusercontent.com/{repo}/main/.env.example -O .env
nano .env
docker run -d --name telegram-monitor --env-file .env {docker_ref}
```

---
[Project Channel](https://t.me/langgefabu) | [Community Group](https://t.me/langgepython)
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build GitHub Release body from CHANGELOG.md")
    parser.add_argument("--version", required=True, help="Release version, for example v2.0.1")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="Path to CHANGELOG.md")
    parser.add_argument("--output", required=True, help="Output markdown file path")
    parser.add_argument("--repo", default=os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY", "luoyanglang/TelegramMonitor"))
    parser.add_argument("--dockerhub-username", default=os.environ.get("DOCKERHUB_USERNAME", "luoyanglangge"))
    parser.add_argument("--docker-image-name", default=os.environ.get("DOCKER_IMAGE_NAME", "telegram-monitor"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    changelog_text = Path(args.changelog).read_text(encoding="utf-8")
    changelog_section = extract_changelog_section(changelog_text, args.version)
    release_body = build_release_body(
        args.version,
        changelog_section,
        args.repo,
        args.dockerhub_username,
        args.docker_image_name,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(release_body, encoding="utf-8")


if __name__ == "__main__":
    main()
