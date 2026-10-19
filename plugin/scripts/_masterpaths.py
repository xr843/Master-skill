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

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In the repository the masters are in prebuilt/. In the plugin bundle
# (plugin/, built by scripts/build-plugin-bundle.py) these scripts sit in
# plugin/scripts/ and the masters in plugin/skills/.
PREBUILT = os.path.join(_ROOT, "prebuilt")
if not os.path.isdir(PREBUILT) and os.path.isdir(os.path.join(_ROOT, "skills")):
    PREBUILT = os.path.join(_ROOT, "skills")


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
