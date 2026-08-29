"""Minimal, preview-first Zotero Web API organizer.

Provide the API key through the ZOTERO_API_KEY environment variable only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any


ROOT = "https://api.zotero.org"


class ZoteroAPI:
    def __init__(self) -> None:
        self.key = os.environ.get("ZOTERO_API_KEY")
        if not self.key:
            raise RuntimeError("Set ZOTERO_API_KEY through a secure credential source before running this tool.")
        identity, _ = self.request("GET", "/keys/current")
        self.user_id = int(identity["userID"])

    @property
    def library(self) -> str:
        return f"/users/{self.user_id}"

    def request(self, method: str, path: str, body: Any | None = None, version: int | None = None) -> tuple[Any, dict[str, str]]:
        headers = {"Zotero-API-Key": self.key, "Zotero-API-Version": "3", "Accept": "application/json"}
        data = None
        if body is not None:
            headers.update({"Content-Type": "application/json", "Zotero-Write-Token": uuid.uuid4().hex})
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        if version is not None:
            headers["If-Unmodified-Since-Version"] = str(version)
        try:
            with urllib.request.urlopen(urllib.request.Request(ROOT + path, headers=headers, data=data, method=method), timeout=30) as response:
                raw = response.read()
                return (json.loads(raw.decode("utf-8")) if raw else {}), dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            if exc.code == 412:
                raise RuntimeError("The remote library changed. Refresh, review the difference, and retry deliberately.") from exc
            raise RuntimeError(f"Zotero API returned HTTP {exc.code}.") from exc

    def library_version(self) -> int:
        _, headers = self.request("GET", f"{self.library}/collections?limit=1")
        value = headers.get("Last-Modified-Version") or headers.get("last-modified-version")
        if value is None:
            raise RuntimeError("The server did not provide a library version for this write.")
        return int(value)

    def item(self, key: str) -> dict[str, Any]:
        result, _ = self.request("GET", f"{self.library}/items/{urllib.parse.quote(key)}")
        return result.get("data", result)


def show(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def verify(_: argparse.Namespace) -> None:
    api = ZoteroAPI()
    data, _ = api.request("GET", "/keys/current")
    user = data.get("access", {}).get("user", {})
    show({"user_id": data.get("userID"), "library_access": bool(user.get("library")), "write_access": bool(user.get("write")), "file_access": bool(user.get("files"))})


def list_collections(_: argparse.Namespace) -> None:
    api = ZoteroAPI()
    rows, start = [], 0
    while True:
        page, _ = api.request("GET", f"{api.library}/collections?limit=100&start={start}")
        rows.extend({"key": x.get("data", x).get("key"), "name": x.get("data", x).get("name"), "parentCollection": x.get("data", x).get("parentCollection")} for x in page)
        if len(page) < 100:
            break
        start += len(page)
    show(rows)


def create_collection(args: argparse.Namespace) -> None:
    api = ZoteroAPI()
    data: dict[str, Any] = {"name": args.name}
    if args.parent_key:
        data["parentCollection"] = args.parent_key
    if not args.apply:
        show({"dry_run": True, "plan": {"create_collection": data}})
        return
    result, _ = api.request("POST", f"{api.library}/collections", [data], api.library_version())
    show({"created": result})


def add_to_collection(args: argparse.Namespace) -> None:
    api = ZoteroAPI()
    item = api.item(args.item_key)
    original = list(item.get("collections", []))
    updated = original if args.collection_key in original else original + [args.collection_key]
    if not args.apply:
        show({"dry_run": True, "plan": {"item_key": args.item_key, "current_collections": original, "result_collections": updated}})
        return
    result, _ = api.request("PATCH", f"{api.library}/items/{urllib.parse.quote(args.item_key)}", {"version": item["version"], "collections": updated}, int(item["version"]))
    if args.collection_key not in api.item(args.item_key).get("collections", []):
        raise RuntimeError("Read-back verification did not find the requested collection membership.")
    show({"updated": result, "verified": True})


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify").set_defaults(run=verify)
    commands.add_parser("list-collections").set_defaults(run=list_collections)
    create = commands.add_parser("create-collection")
    create.add_argument("--name", required=True)
    create.add_argument("--parent-key")
    create.add_argument("--apply", action="store_true")
    create.set_defaults(run=create_collection)
    membership = commands.add_parser("add-to-collection")
    membership.add_argument("--item-key", required=True)
    membership.add_argument("--collection-key", required=True)
    membership.add_argument("--apply", action="store_true")
    membership.set_defaults(run=add_to_collection)
    args = parser.parse_args()
    try:
        args.run(args)
        return 0
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

