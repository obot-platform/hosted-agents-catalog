"""Validate the hosted agent catalog.

Obot discovers definitions by filename anywhere in the tree -- every
harness.yaml and agent.yaml is one -- and a definition it cannot parse or
resolve fails the whole source's sync. Catching that here means a broken entry
never reaches an installation.

The checks mirror what Obot itself enforces at sync, so a pull request that
passes is one that will sync.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

HARNESS = "harness.yaml"
AGENT = "agent.yaml"

# A protocol is a request format rather than a vendor: a client written for one
# cannot talk to another.
MODEL_APIS = {"anthropic", "openai-responses", "openai-chat-completions"}


def find_duplicate_keys(node, path):
    """Duplicate keys parse silently, with the last one winning."""
    errors = []
    if isinstance(node, yaml.MappingNode):
        keys = set()
        for key_node, value_node in node.value:
            key = key_node.value
            if key in keys:
                errors.append(f"{path}:{key_node.start_mark.line + 1}: duplicate key {key!r}")
            keys.add(key)
            errors.extend(find_duplicate_keys(value_node, path))
    elif isinstance(node, yaml.SequenceNode):
        for value_node in node.value:
            errors.extend(find_duplicate_keys(value_node, path))
    return errors


def load(path, errors):
    try:
        errors.extend(find_duplicate_keys(yaml.compose(path.read_text()), path))
        return yaml.safe_load(path.read_text())
    except yaml.YAMLError as error:
        errors.append(f"{path}: invalid YAML: {error}")
        return None


def main() -> int:
    root = Path(".")
    errors: list[str] = []

    harnesses = {}
    for path in sorted(root.rglob(HARNESS)):
        if ".git" in path.parts:
            continue
        data = load(path, errors)
        if data is None:
            continue
        rel = path.as_posix()
        harnesses[rel] = data
        if not data.get("name"):
            errors.append(f"{rel}: name is required")
        if not data.get("image"):
            errors.append(f"{rel}: image is required")

    for path in sorted(root.rglob(AGENT)):
        if ".git" in path.parts:
            continue
        data = load(path, errors)
        if data is None:
            continue
        rel = path.as_posix()

        if not data.get("name"):
            errors.append(f"{rel}: name is required")

        # An agent names its harness by that harness's path in this repository.
        # Obot rewrites it to the stored ID at sync, so a path that does not
        # exist here is an agent that can never run.
        harness_id = data.get("harnessID")
        if not harness_id:
            errors.append(f"{rel}: harnessID is required")
        elif harness_id not in harnesses:
            errors.append(
                f"{rel}: harnessID {harness_id!r} does not name a harness in this repository; "
                f"expected one of {sorted(harnesses)}"
            )
        else:
            # A terminal attaches to a console the container was started with,
            # so it needs a harness that asked for one.
            if data.get("terminal") and not harnesses[harness_id].get("interactive"):
                errors.append(
                    f"{rel}: offers a terminal but {harness_id} is not interactive, "
                    "so there is no console to attach to"
                )

        # A secret in source control is a secret that has leaked. Obot rejects
        # this at sync too; failing here keeps it out of the history.
        for env in data.get("env") or []:
            if env.get("sensitive") and env.get("value"):
                errors.append(f"{rel}: sensitive env {env.get('key')!r} must not carry a value")

        port = data.get("port")
        if port is not None and not (0 < int(port) < 65536):
            errors.append(f"{rel}: port {port} is out of range")

        if data.get("gitRef") and not data.get("gitRepo"):
            errors.append(f"{rel}: gitRef names a revision of nothing without gitRepo")

    for path in sorted(root.rglob(HARNESS)):
        if ".git" in path.parts:
            continue
        api = (harnesses.get(path.as_posix()) or {}).get("modelAPI")
        if api and api not in MODEL_APIS:
            errors.append(f"{path}: modelAPI {api!r} must be one of {sorted(MODEL_APIS)}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"Catalog is valid: {len(harnesses)} harness(es), "
          f"{len(list(root.rglob(AGENT)))} agent(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
