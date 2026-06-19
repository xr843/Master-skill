"""Shared prebuilt-master directory resolution for the offline helper scripts.

`prebuilt/` dirs are named `master-<slug>` (e.g. `master-huineng`), but the
SKILL.md docs — and users — invoke the scripts with the short slug
(`--master huineng`). Resolving only the literal value meant the documented
short-name invocation silently found nothing for all 14 masters. This mirrors
`resolveMasterDir` in `bin/cli.mjs`: try the value as given, then `master-<value>`.

Callers are expected to validate the slug charset first (see `_SAFE_MASTER`),
so this only does path resolution, never path-traversal guarding.
"""
import os

PREBUILT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prebuilt")


def resolve_master_dir(master, base=PREBUILT):
    """Return the prebuilt dir for `master`, or None if it doesn't exist.

    Tries `<master>` first, then `master-<master>`, so both `huineng` and
    `master-huineng` resolve to `prebuilt/master-huineng`.

    Callers should still charset-check the slug (see `_SAFE_MASTER`), but as
    defense in depth this never returns a path outside `base`: an absolute
    value (`/etc`) or `..` traversal resolves outside and yields None.
    """
    base_abs = os.path.abspath(base)
    for candidate in (master, f"master-{master}"):
        path = os.path.join(base, candidate)
        if os.path.isdir(path) and os.path.abspath(path).startswith(base_abs + os.sep):
            return path
    return None
