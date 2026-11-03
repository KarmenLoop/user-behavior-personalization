#!/usr/bin/env python3
"""Check the public instruction package using the Python standard library."""

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "SKILL.md",
    "LICENSE",
    "NOTICE",
    "VERSION",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "agents/openai.yaml",
    "references/profile-format.md",
    "references/reflection-workflow.md",
    "assets/templates/USER_SKILL.md",
    "assets/templates/REFLECTION.md",
    "assets/templates/state.json",
    "docs/quickstart.md",
    "docs/architecture.md",
    "docs/host-integration.md",
    "docs/privacy-and-memory-control.md",
    "docs/evaluation.md",
    "examples/conversations.md",
    "examples/USER_SKILL.md",
    "examples/daily-reflection.md",
)
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^\n)]+)\)")
PRIVATE_DIRS = {"profiles", "private-memory", "user-data", "memory", "reflections", "versions"}
EXCLUDED_DIRS = {".git", ".validation", "__pycache__"}
MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024


def check():
    errors = []
    files = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            errors.append(f"Symlink is not permitted in the release package: {relative}")
            continue
        if path.is_dir():
            if path.name in PRIVATE_DIRS:
                errors.append(f"Unexpected private-data directory: {relative}")
            continue
        files.append(path)

    for name in REQUIRED:
        if not (ROOT / name).is_file():
            errors.append(f"Missing required file: {name}")

    for path in files:
        relative = path.relative_to(ROOT)
        if path.name == "state.json" and relative.as_posix() != "assets/templates/state.json":
            errors.append(f"Unexpected live state file: {relative}")
        if path.name.startswith(".env") or path.suffix in {".pem", ".key"}:
            errors.append(f"Potential local configuration or credential file: {relative}")
        try:
            if path.suffix.lower() == ".jpg":
                if relative.parts[:2] != ("docs", "images"):
                    errors.append(f"JPEG screenshots must be inside docs/images: {relative}")
                    continue
                # Bound the read as well as the accepted file size. A screenshot
                # is the only binary format allowed in this source package.
                with path.open("rb") as stream:
                    image = stream.read(MAX_SCREENSHOT_BYTES + 1)
                if len(image) > MAX_SCREENSHOT_BYTES:
                    errors.append(f"JPEG screenshot exceeds 5 MiB: {relative}")
                    continue
                if not image.startswith(b"\xff\xd8\xff") or not image.endswith(b"\xff\xd9"):
                    errors.append(f"Invalid JPEG screenshot signature: {relative}")
                    continue
                # Check textual metadata for the same private paths as text
                # files; allowing screenshots must not bypass that check.
                content = image.decode("utf-8", errors="ignore")
            else:
                content = path.read_text(encoding="utf-8")
                if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", content):
                    errors.append(f"Unexpected binary content: {relative}")
        except (UnicodeError, OSError) as exc:
            errors.append(f"Cannot read release text {relative}: {exc}")
            continue
        # Public language guides, multilingual parsers, and synthetic fixtures
        # intentionally contain both English and Chinese text.
        mac_user_prefix = "/" + "Users" + "/"
        windows_user_prefix = "C:" + chr(92) + "Users" + chr(92)
        if mac_user_prefix in content or windows_user_prefix in content:
            errors.append(f"Machine-specific user path found: {relative}")
        if path.suffix != ".md":
            continue

        fence = None
        prose = []
        for number, line in enumerate(content.splitlines(), 1):
            marker = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
            if marker:
                sequence, suffix = marker.groups()
                if fence is None:
                    fence = (sequence[0], len(sequence), number)
                elif sequence[0] == fence[0] and len(sequence) >= fence[1] and not suffix.strip():
                    fence = None
                continue
            if fence is None:
                prose.append(line)
        if fence is not None:
            errors.append(f"Unclosed fenced block: {relative}:{fence[2]}")

        for match in LINK.finditer("\n".join(prose)):
            target = match.group(1).split(' "', 1)[0].strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = (path.parent / unquote(parsed.path)).resolve()
            try:
                destination.relative_to(ROOT)
            except ValueError:
                errors.append(f"Local link escapes package: {relative} -> {target}")
                continue
            if not destination.exists():
                errors.append(f"Broken local file link: {relative} -> {target}")

    try:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        header = re.match(r"\A---\n(.*?)\n---\n", skill, re.DOTALL)
        if not header:
            errors.append("SKILL.md must start with YAML frontmatter")
        else:
            for field in ("name", "description", "license"):
                if not re.search(rf"^{field}:\s*\S", header.group(1), re.MULTILINE):
                    errors.append(f"Missing skill frontmatter field: {field}")
            if "name: user-behavior-personalization" not in header.group(1):
                errors.append("Unexpected skill name")
            if "license: Apache-2.0" not in header.group(1):
                errors.append("Skill must declare the selected Apache-2.0 license")
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        if "Apache License" not in license_text or "Version 2.0, January 2004" not in license_text:
            errors.append("LICENSE is not the expected Apache-2.0 text")
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
            errors.append("VERSION must contain a semantic version")
        state = json.loads((ROOT / "assets/templates/state.json").read_text(encoding="utf-8"))
        if state != {
            "schema_version": 1,
            "user_id": None,
            "profile_version": 0,
            "last_reflection_at": None,
            "conversation_cursors": {},
            "last_batch_id": None,
        }:
            errors.append("State template must remain blank and match the documented initial format")
    except (OSError, ValueError) as exc:
        errors.append(f"Required artifact validation failed: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAILED: {len(errors)} package issue(s)", file=sys.stderr)
        return 1
    print(f"PASS: {len(files)} package files; required artifacts, local file links, fences, basic frontmatter, blank state, screenshot format, and publication hygiene checked.")
    print("SCOPE: No live-agent behavior, scheduler, synchronization, or host integration was executed.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
