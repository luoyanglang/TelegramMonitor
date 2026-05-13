import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request


MESSAGE_ID_RE = re.compile(r"<!--\s*telegram_message_id:(\d+)\s*-->")
SECTION_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")
LIST_RE = re.compile(r"^\s*[-*]\s+(.*)$")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
BACKTICK_RE = re.compile(r"`([^`]+)`")


def github_request(method, path, token, payload=None):
    url = f"https://api.github.com{path}"
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "telegram-monitor-release-sync",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def telegram_request(method, token, payload):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def strip_comments(text):
    return MESSAGE_ID_RE.sub("", text).strip()


def clean_markdown(text):
    text = LINK_RE.sub(r"\1", text)
    text = BACKTICK_RE.sub(r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"\s+by\s+@[\w-]+(?:\s+in\s+#\d+)?$", "", text)
    text = re.sub(r"\s+in\s+#\d+$", "", text)
    return text.strip()


def collect_section_items(body, headings):
    items = []
    active = False
    in_code = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading_match = SECTION_RE.match(line)
        if heading_match:
            heading = heading_match.group(1).strip().lower()
            if active:
                break
            active = any(key in heading for key in headings)
            continue
        if not active:
            continue
        item_match = LIST_RE.match(line)
        if item_match:
            item = clean_markdown(item_match.group(1))
            if item:
                items.append(item)
    return items


def collect_fallback_items(body):
    items = []
    in_code = False
    ignore_section = False
    ignored_headings = ("downloads", "quick start", "docker", "feedback")
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading_match = SECTION_RE.match(line)
        if heading_match:
            heading = heading_match.group(1).strip().lower()
            ignore_section = any(key in heading for key in ignored_headings)
            continue
        if ignore_section:
            continue
        item_match = LIST_RE.match(line)
        if item_match:
            item = clean_markdown(item_match.group(1))
            if item:
                items.append(item)
    return items


def extract_highlights(body):
    clean_body = strip_comments(body)
    items = collect_section_items(clean_body, ("highlights", "update notes", "更新内容", "本次更新"))
    if not items:
        items = collect_fallback_items(clean_body)
    deduped = []
    seen = set()
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:4]


def build_message(release):
    tag = release["tag_name"]
    release_url = release["html_url"]

    highlights = extract_highlights(release.get("body") or "")
    if highlights:
        highlight_block = "\n".join(f"- {html.escape(item)}" for item in highlights)
    else:
        highlight_block = "• Details are available on the GitHub Release page."

    return (
        f"<b>Telegram Monitor {html.escape(tag)}</b>\n\n"
        f"<b>Highlights:</b>\n{highlight_block}\n\n"
        f"<b>Release:</b>\n"
        f"<a href=\"{html.escape(release_url, quote=True)}\">GitHub Release</a>"
    )


def sync_release_body(repo, release_id, body, message_id, token):
    marker = f"<!-- telegram_message_id:{message_id} -->"
    if MESSAGE_ID_RE.search(body or ""):
        updated_body = MESSAGE_ID_RE.sub(marker, body or "", count=1)
    else:
        updated_body = (body or "").rstrip() + f"\n\n{marker}\n"
    github_request(
        "PATCH",
        f"/repos/{repo}/releases/{release_id}",
        token,
        {"body": updated_body},
    )


def main():
    repo = os.environ["REPO"]
    release_id = os.environ.get("RELEASE_ID")
    tag_name = os.environ.get("TAG_NAME")
    github_token = os.environ["GITHUB_TOKEN"]
    telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]

    if release_id:
        release = github_request(
            "GET",
            f"/repos/{repo}/releases/{release_id}",
            github_token,
        )
    elif tag_name:
        encoded_tag = urllib.parse.quote(tag_name, safe="")
        release = github_request(
            "GET",
            f"/repos/{repo}/releases/tags/{encoded_tag}",
            github_token,
        )
        release_id = str(release["id"])
    else:
        raise RuntimeError("RELEASE_ID or TAG_NAME is required.")

    message = build_message(release)

    existing_message_id = None
    body = release.get("body") or ""
    match = MESSAGE_ID_RE.search(body)
    if match:
        existing_message_id = match.group(1)

    payload = {
        "chat_id": channel_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }

    result = None
    if existing_message_id:
        try:
            result = telegram_request(
                "editMessageText",
                telegram_token,
                {**payload, "message_id": existing_message_id},
            )
        except urllib.error.HTTPError:
            existing_message_id = None

    if not existing_message_id:
        result = telegram_request("sendMessage", telegram_token, payload)
        existing_message_id = str(result["result"]["message_id"])

    sync_release_body(repo, release_id, body, existing_message_id, github_token)
    print(
        json.dumps(
            {
                "release_id": release_id,
                "tag": release["tag_name"],
                "message_id": existing_message_id,
                "ok": result["ok"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
