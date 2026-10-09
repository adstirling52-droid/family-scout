"""Command line: print the digest, or send it."""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from planner.config import RECIPIENT
from planner.digest import build_digest
from planner.mailer import MailConfigError, load_smtp, send_email
from planner.render import render_html, render_text, subject
from planner.weekend import is_send_window


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Livingston family weekend list and optionally email it."
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Email the digest now, ignoring the Friday 10:00 window.",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Email from 10:00 Europe/London on Friday, including a late start.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv()

    if args.scheduled and not args.send:
        now = datetime.now(ZoneInfo("Europe/London"))
        if not is_send_window(now):
            print(
                f"Not sending. It is {now.strftime('%A %H:%M')} Europe/London, "
                "and the digest sends from 10:00 on Friday, including a late start."
            )
            return 0

    digest = build_digest()
    text = render_text(
        digest.saturday,
        digest.sunday,
        digest.forecast,
        digest.free,
        digest.paid,
        digest.notes,
    )
    html = render_html(
        digest.saturday,
        digest.sunday,
        digest.forecast,
        digest.free,
        digest.paid,
        digest.notes,
    )
    title = subject(digest.saturday, digest.sunday)

    if not args.send and not args.scheduled:
        print(text)
        return 0

    try:
        settings = load_smtp(RECIPIENT)
        send_email(settings, title, text, html)
    except MailConfigError as exc:
        print(str(exc), file=sys.stderr)
        print(text)
        return 1

    print(f"Sent '{title}' to {settings.recipient}.")
    return 0
