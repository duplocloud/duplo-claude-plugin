#!/usr/bin/env python3
"""Queue-backed mirroring helper.

Stores mirror payloads in a local JSONL queue and flushes them to the
helpdesk ticket endpoint in order. This prevents transient losses when hooks
fire asynchronously.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone


def split_readable(message: str, limit: int) -> list[str]:
    if len(message) <= limit:
        return [message]

    sentences: list[str] = []
    for line in message.splitlines(keepends=True):
        parts = re.findall(r".*?(?:[.!?](?:\s+|$)|$)", line, flags=re.S)
        sentences.extend([p for p in parts if p])

    if not sentences:
        sentences = [message]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > limit:
            words = re.findall(r"\S+\s*", sentence)
            for word in words:
                if len(current) + len(word) > limit and current:
                    chunks.append(current)
                    current = ""
                if len(word) > limit:
                    if current:
                        chunks.append(current)
                        current = ""
                    for i in range(0, len(word), limit):
                        chunks.append(word[i : i + limit])
                else:
                    current += word
            continue

        if len(current) + len(sentence) > limit and current:
            chunks.append(current)
            current = ""
        current += sentence

    if current:
        chunks.append(current)

    return [c for c in chunks if c]


def read_queue(queue_file: str) -> list[dict]:
    if not os.path.exists(queue_file):
        return []

    entries: list[dict] = []
    with open(queue_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    entries.append(obj)
            except Exception:
                continue
    return entries


def write_queue(queue_file: str, entries: list[dict]) -> None:
    parent = os.path.dirname(queue_file) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="mirror-queue-", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        os.replace(tmp, queue_file)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def enqueue(queue_file: str, role: str, source: str, content: str) -> None:
    content = content or ""
    if not content.strip():
        return

    role = role if role in {"user", "assistant"} else "assistant"
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "role": role,
        "content": content,
        "message_mode": 1,
        "source": source,
    }

    parent = os.path.dirname(queue_file) or "."
    os.makedirs(parent, exist_ok=True)
    with open(queue_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def post_message(
    workspace_id: str,
    ticket_name: str,
    token: str,
    role: str,
    content: str,
) -> None:
    url = (
        f"http://localhost:60021/v1/aiservicedesk/tickets/"
        f"{workspace_id}/{ticket_name}/sendMessage"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = json.dumps(
        {
            "content": content,
            "role": role,
            "message_mode": 1,
            "data": {},
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=20):
        pass


def flush(
    queue_file: str,
    workspace_id: str,
    ticket_name: str,
    token: str,
    max_chars: int,
) -> None:
    entries = read_queue(queue_file)
    if not entries:
        return

    remaining: list[dict] = []
    for entry in entries:
        role = str(entry.get("role", "assistant"))
        content = str(entry.get("content", ""))

        if not content.strip():
            continue

        ok = True
        try:
            for chunk in split_readable(content, max_chars):
                post_message(workspace_id, ticket_name, token, role, chunk)
        except Exception:
            ok = False

        if not ok:
            remaining.append(entry)

    write_queue(queue_file, remaining)


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    cmd = sys.argv[1]

    if cmd == "enqueue":
        if len(sys.argv) < 5:
            return 0
        queue_file = sys.argv[2]
        role = sys.argv[3]
        source = sys.argv[4]
        content = sys.stdin.read()
        enqueue(queue_file, role, source, content)
        return 0

    if cmd == "flush":
        if len(sys.argv) < 7:
            return 0
        queue_file = sys.argv[2]
        workspace_id = sys.argv[3]
        ticket_name = sys.argv[4]
        token = sys.argv[5]
        try:
            max_chars = max(1000, int(sys.argv[6]))
        except Exception:
            max_chars = 12000
        flush(queue_file, workspace_id, ticket_name, token, max_chars)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
