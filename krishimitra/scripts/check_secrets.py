#!/usr/bin/env python3
"""
Secret scanner for this repo. Standard library only. Prints file:line + rule name, NEVER the secret itself.

  python scripts/check_secrets.py            # scan every file git would add (tracked + untracked, not ignored)
  python scripts/check_secrets.py --staged   # scan only what is staged for commit

Exit code 0 = nothing found, 1 = findings (do not commit/push until resolved).
"""
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_NAMES = [".env", ".env.*", "*.pem", "*.key", "*.p12", "*.db", "*.sqlite", "*.sqlite3", "credentials*.json", "service-account*.json", "id_rsa*"]
ALLOWED_NAMES = {".env.example"}
SKIP_CONTENT = {"package-lock.json"}
RULES = [
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Long hex string (possible API key)", re.compile(r"\b[0-9a-fA-F]{40,}\b")),
    ("Credential assignment", re.compile(r"""(?i)\b[\w-]*(?:api[_-]?key|secret|token|password|passwd)[\w-]*\s*[:=]\s*["']?([A-Za-z0-9_\-./+=]{16,})""")),
]
CODE_REF = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$")   # e.g. s.gemini_api_key (a variable, not a value)
PLACEHOLDER = re.compile(r"(?i)(your[_-]|<|xxx|changeme|example|placeholder|dummy|test|process\.env|import\.meta|os\.environ|get_settings|\.\.\.)")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def files(staged: bool):
    out = git("diff", "--cached", "--name-only", "--diff-filter=ACMR") if staged else git("ls-files", "--cached", "--others", "--exclude-standard")
    return [f for f in out.splitlines() if f]


def main():
    staged = "--staged" in sys.argv
    try:
        names = files(staged)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Not a git repository (run `git init` first) or git is not installed.")
        return 2
    findings = []
    for rel in names:
        base = Path(rel).name
        if base not in ALLOWED_NAMES and any(fnmatch.fnmatch(base, pat) for pat in FORBIDDEN_NAMES):
            findings.append((rel, 0, "Forbidden file type (should be git-ignored)"))
            continue
        path = ROOT / rel
        if base in SKIP_CONTENT or not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(lines, 1):
            for name, rx in RULES:
                m = rx.search(line)
                if not m:
                    continue
                value = m.group(1) if m.groups() else m.group(0)
                if name in ("Credential assignment", "Long hex string (possible API key)") and PLACEHOLDER.search(line):
                    continue
                if name == "Credential assignment" and CODE_REF.match(value):
                    continue
                findings.append((rel, n, name))
                break
    print(f"Scanned {len(names)} {'staged' if staged else 'candidate'} files.")
    if staged:
        print("Staged files:\n  " + "\n  ".join(names))
    if findings:
        print(f"\n{len(findings)} POSSIBLE SECRET(S) FOUND - do not commit or push:")
        for rel, n, name in findings:
            print(f"  {rel}{':' + str(n) if n else ''}  -> {name}")
        return 1
    print("No secrets or forbidden files found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
