#!/usr/bin/env python3
"""Assert the pinned eval SDKs still expose what test-fidelity.py calls.

`npm test` proves nothing about these. The grading path never runs without an
API key, so a breaking change in the anthropic or openai SDK stays invisible
until someone spends money on a sweep — which is exactly when it is most
expensive to discover. Dependabot has proposed four bumps of these two
packages in one week, each with a green tick.

So this is the check that has to exist: import whatever is installed and read
the surface, the same way it was read by hand when the pins were written.

    python3 scripts/check-eval-sdk-surface.py

Exits 1 naming anything missing. Not wired into `npm test`: the SDKs are not in
requirements.txt and a plain contributor has no reason to install them. Run it
when reviewing a bump — CONTRIBUTING § 7 says so.
"""

from __future__ import annotations

import importlib
import inspect
import sys

# Exactly what scripts/test-fidelity.py touches. Nothing aspirational: a
# surface check that guards more than the code uses turns an irrelevant
# upstream change into a blocked upgrade.
REQUIRED = {
    "anthropic": {
        "client_kwargs": ["api_key", "max_retries"],
        "create_params": ["model", "max_tokens", "system", "messages", "timeout"],
        "model_fields": {
            "Message": ["stop_reason"],
            "TextBlock": ["text"],
            # Read by the prompt-cache reporting.
            "Usage": ["cache_read_input_tokens", "cache_creation_input_tokens"],
        },
    },
    "openai": {
        "client_kwargs": ["api_key", "base_url", "max_retries"],
        "create_params": ["model", "max_tokens", "messages", "timeout"],
        "model_fields": {},
    },
}


def _missing_for(name: str, spec: dict) -> list[str]:
    try:
        module = importlib.import_module(name)
    except ImportError:
        return [f"{name} is not installed (pip install -r requirements-eval.txt)"]

    problems: list[str] = []
    version = getattr(module, "__version__", "?")

    client_cls = module.Anthropic if name == "anthropic" else module.OpenAI
    init_params = inspect.signature(client_cls.__init__).parameters
    for kwarg in spec["client_kwargs"]:
        if kwarg not in init_params:
            problems.append(f"{name} {version}: {client_cls.__name__}({kwarg}=) is gone")

    # Constructing the client is part of the check: anthropic 1.x moved to
    # httpx2 and raises here on a machine with a SOCKS proxy unless `socksio`
    # is present, which is worth failing loudly rather than at sweep time.
    try:
        kwargs = {"api_key": "surface-check"}
        if name == "openai":
            kwargs["base_url"] = "https://invalid.example/v1"
        client = client_cls(**kwargs)
    except Exception as error:  # noqa: BLE001 - any failure here blocks a sweep
        return problems + [f"{name} {version}: client construction failed: {error}"]

    create = client.messages.create if name == "anthropic" else client.chat.completions.create
    params = inspect.signature(create).parameters
    for param in spec["create_params"]:
        if param not in params and "kwargs" not in params:
            problems.append(f"{name} {version}: create({param}=) is gone")

    if spec["model_fields"]:
        types_module = importlib.import_module(f"{name}.types")
        for cls_name, fields in spec["model_fields"].items():
            cls = getattr(types_module, cls_name, None)
            if cls is None:
                problems.append(f"{name} {version}: types.{cls_name} is gone")
                continue
            declared = getattr(cls, "model_fields", {})
            for field in fields:
                if field not in declared:
                    problems.append(f"{name} {version}: {cls_name}.{field} is gone")
    return problems


def _pinned_versions() -> dict[str, str]:
    """What requirements-eval.txt pins, so the check can say whose surface it read."""
    import re
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent / "requirements-eval.txt").read_text(
        encoding="utf-8"
    )
    return dict(re.findall(r"^([a-z-]+)==([\d.]+)$", text, re.M))


def main() -> int:
    problems: list[str] = []
    pinned = _pinned_versions()

    for name, spec in REQUIRED.items():
        problems += _missing_for(name, spec)

    # The installed version has to be the pinned one, or this reports on a
    # surface nobody ships. Caught the first time it ran: the system Python had
    # anthropic 0.122.0 while the file pinned 1.4.0, and the check passed —
    # green about a package the sweep will not use.
    for name, want in pinned.items():
        try:
            have = getattr(importlib.import_module(name), "__version__", None)
        except ImportError:
            continue  # already reported above
        if have and have != want:
            problems.append(
                f"{name}: requirements-eval.txt pins {want} but {have} is "
                "installed — this check just read the wrong package"
            )

    if problems:
        print(f"✗ {len(problems)} eval-SDK surface problem(s):\n")
        for problem in problems:
            print(f"  - {problem}")
        print("\nA bump that removes any of these breaks the sweep, not the CI.")
        return 1

    versions = ", ".join(
        f"{n} {getattr(importlib.import_module(n), '__version__', '?')}" for n in REQUIRED
    )
    print(f"✓ eval SDK surface intact — {versions}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
