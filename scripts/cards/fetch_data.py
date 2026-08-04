#!/usr/bin/env python3
"""Fetch GitHub profile metrics via GraphQL into data.json."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

GQL_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!, $repoCursor: String) {
  user(login: $login) {
    followers {
      totalCount
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
    repositories(
      first: 100
      after: $repoCursor
      ownerAffiliations: OWNER
      isFork: false
      orderBy: { field: UPDATED_AT, direction: DESC }
    ) {
      totalCount
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        stargazerCount
        forkCount
        primaryLanguage {
          name
          color
        }
        languages(first: 10, orderBy: { field: SIZE, direction: DESC }) {
          edges {
            size
            node {
              name
              color
            }
          }
        }
      }
    }
  }
}
"""


def gql(token: str, variables: dict) -> dict:
    body = json.dumps({"query": QUERY, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        GQL_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "YunfanGoForIt-profile-cards",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GraphQL HTTP {e.code}: {detail}") from e

    if "errors" in payload:
        raise SystemExit(f"GraphQL errors: {json.dumps(payload['errors'], ensure_ascii=False)}")
    return payload["data"]


def fetch_user(token: str, login: str) -> dict:
    nodes: list[dict] = []
    total_count = 0
    cursor = None
    base_user = None

    while True:
        data = gql(token, {"login": login, "repoCursor": cursor})
        user = data.get("user")
        if not user:
            raise SystemExit(f"User not found: {login}")

        if base_user is None:
            base_user = {
                "followers": user["followers"],
                "contributionsCollection": user["contributionsCollection"],
            }

        repos = user["repositories"]
        total_count = repos["totalCount"]
        nodes.extend(repos["nodes"] or [])
        page = repos["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]

    return {
        **base_user,
        "repositories": {
            "totalCount": total_count,
            "nodes": nodes,
        },
    }


def main() -> None:
    login = os.environ.get("GITHUB_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not login:
        raise SystemExit("Set GITHUB_LOGIN or GITHUB_REPOSITORY_OWNER")
    if not token:
        raise SystemExit("Set GITHUB_TOKEN or GH_TOKEN")

    out = Path(__file__).resolve().parent / "data.json"
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])

    data = fetch_user(token, login)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    n = data["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
    contribs = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    print(f"Wrote {out} — {n} repos, {stars} stars, {contribs} contributions")


if __name__ == "__main__":
    main()
