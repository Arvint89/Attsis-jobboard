"""Bulk-run the JB-43 resolver against every platform:"resolve" entry (JB-5).

Reads engine/companies.json, iterates the resolve-tier entries, and for each
one asks resolver.Resolver.resolve(careers_url) what ATS the page uses.
Prints a per-entry line and a summary. No writes -- outcomes go to the log
so a human can review before a bulk-update PR promotes entries to their
real platforms.

Meant for CI (resolve-sweep.yml, workflow_dispatch); sandbox has no
outbound network to careers pages. Exit code is always 0.
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "engine"))

import resolver  # noqa: E402


def main() -> int:
    with open(os.path.join(ROOT, "engine", "companies.json"), encoding="utf-8") as f:
        registry = json.load(f)

    resolve_entries = [c for c in registry["companies"] if c.get("platform") == "resolve"]
    print(f"Sweeping {len(resolve_entries)} resolve-tier entries\n")

    r = resolver.Resolver(cache=resolver.load_cache(), max_lookups=len(resolve_entries) + 10)

    supported_hits = []   # (name, platform, slug) -- ready to promote
    unsupported_hits = []  # (name, platform, slug) -- known ATS, no adapter yet
    misses = []            # (name, url) -- resolver returned None
    no_url = []            # (name,) -- no careers_url in registry

    for c in resolve_entries:
        name = c["name"]
        url = c.get("careers_url", "")
        if not url:
            no_url.append(name)
            print(f"  SKIP  {name}: no careers_url")
            continue
        det = r.resolve(url)
        if det is None:
            misses.append((name, url))
            print(f"  MISS  {name}: {url}")
        elif det.get("supported"):
            supported_hits.append((name, det["platform"], det.get("slug", "")))
            print(f"  HIT+  {name}: {det['platform']} slug={det.get('slug','')!r}")
        else:
            unsupported_hits.append((name, det["platform"], det.get("slug", "")))
            print(f"  HIT-  {name}: {det['platform']} (no adapter yet) slug={det.get('slug','')!r}")

    print("\n=== SUMMARY")
    print(f"  Supported hits (ready to promote): {len(supported_hits)}")
    print(f"  Unsupported hits (adapter gap):    {len(unsupported_hits)}")
    print(f"  Misses:                            {len(misses)}")
    print(f"  No careers_url:                    {len(no_url)}")
    print(f"  Resolver stats: {r.stats}")

    if supported_hits:
        print("\n=== SUPPORTED HITS (JSON, paste-ready for the promotion PR)")
        promo = [{"name": n, "platform": p, "slug": s} for n, p, s in supported_hits]
        print(json.dumps(promo, indent=2))

    if unsupported_hits:
        print("\n=== UNSUPPORTED HITS (adapter gaps -- ordered by frequency)")
        from collections import Counter
        c = Counter(p for _, p, _ in unsupported_hits)
        for platform, count in c.most_common():
            print(f"  {platform}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
