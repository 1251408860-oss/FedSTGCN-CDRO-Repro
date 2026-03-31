#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http.cookies import SimpleCookie

import requests


ITEM_ID = "53034f60-d215-44b0-a198-eb8a5229218e"
BITSTREAM_ID = "b1b0c077-6f87-4160-8659-9dc34e269e3d"
BASE_URL = "https://idus.us.es"


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "FedSTGCN-BiblioUS17-RequestHelper/1.0"})
    return session


def get_xsrf_token(session: requests.Session) -> str:
    resp = session.get(f"{BASE_URL}/server/api/security/csrf", timeout=30)
    resp.raise_for_status()
    token = session.cookies.get("DSPACE-XSRF-COOKIE", "")
    if token:
        return token
    raw = resp.headers.get("set-cookie", "")
    cookie = SimpleCookie()
    cookie.load(raw)
    morsel = cookie.get("DSPACE-XSRF-COOKIE")
    if morsel is None:
        raise RuntimeError("Could not obtain DSPACE-XSRF-COOKIE from idUS")
    return morsel.value


def check_access(session: requests.Session) -> dict[str, int]:
    base = (
        f"{BASE_URL}/server/api/authz/authorizations/search/object"
        f"?uri={BASE_URL}/server/api/core/bitstreams/{BITSTREAM_ID}"
    )
    can_download = session.get(f"{base}&feature=canDownload&embed=feature", timeout=30)
    can_request = session.get(f"{base}&feature=canRequestACopy&embed=feature", timeout=30)
    can_download.raise_for_status()
    can_request.raise_for_status()
    return {
        "can_download_matches": int(can_download.json().get("page", {}).get("totalElements", 0)),
        "can_request_matches": int(can_request.json().get("page", {}).get("totalElements", 0)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Submit an idUS request-a-copy for Biblio-US17")
    ap.add_argument("--name", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--message", default="Research reproduction request for the Biblio-US17 benchmark.")
    ap.add_argument("--captcha-payload", default="")
    ap.add_argument("--allfiles", action="store_true", help="Request all restricted files under the item")
    ap.add_argument("--dry-run", action="store_true", help="Validate endpoint access and print payload without POSTing")
    args = ap.parse_args()

    session = build_session()
    access = check_access(session)
    xsrf = get_xsrf_token(session)
    payload = {
        "bitstreamId": BITSTREAM_ID,
        "itemId": ITEM_ID,
        "requestEmail": str(args.email),
        "requestName": str(args.name),
        "requestMessage": str(args.message),
        "allfiles": bool(args.allfiles),
    }

    if bool(args.dry_run):
        print(json.dumps({"access": access, "payload": payload}, indent=2))
        return

    headers = {"X-XSRF-TOKEN": xsrf}
    if str(args.captcha_payload).strip():
        headers["x-captcha-payload"] = str(args.captcha_payload).strip()

    resp = session.post(
        f"{BASE_URL}/server/api/tools/itemrequests",
        json=payload,
        headers=headers,
        timeout=30,
    )
    body = resp.text.strip()
    if resp.status_code not in {200, 201, 204}:
        raise RuntimeError(
            f"idUS request-a-copy failed with HTTP {resp.status_code}: {body[:800] or '<empty body>'}"
        )

    print(
        json.dumps(
            {
                "status": resp.status_code,
                "access": access,
                "message": "Request submitted. Wait for idUS / dataset-owner approval email.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
