#!/usr/bin/env python3
"""Deterministic checks for this repository. Python 3 standard library only.

    python3 scripts/verify.py              # offline checks
    python3 scripts/verify.py --check-cli  # also checks orca commands against this host

Exit status: 0 when every check passes, 1 when any check reports a problem.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

ALLOWED_FRONT_MATTER_KEYS = ("name", "description")
PUBLIC_SKILLS = (
    "bot-items", "change-plan", "delivery-review", "event-driven-waits", "model-routing",
    "multi-level-orchestration", "real-environment-proof", "rehearse-risky-operations",
    "secrets-and-workers", "worker-brief-builder", "worker-ops-hygiene",
)
TIERS = ("Basic", "Advanced")
SEMVER = r"\d+\.\d+\.\d+"

# Dashes are written as escapes so this file does not trip its own prose check.
DASHES = {"\u2014": "em dash", "\u2013": "en dash"}

BANNED_WORDS = [
    "delve", "delves", "delving", "leverage", "leverages", "leveraging", "seamless",
    "seamlessly", "robust", "cutting-edge", "game-changer", "game-changing", "supercharge",
    "revolutionize", "revolutionary", "unleash", "empower", "empowers", "elevate", "tapestry",
    "testament", "plethora", "myriad", "synergy", "holistic", "best-in-class", "world-class",
    "state-of-the-art", "next-level", "effortless", "effortlessly", "furthermore", "moreover",
    "paradigm", "unlock", "unlocks", "landscape", "realm", "embark", "meticulous",
    "meticulously", "pivotal", "groundbreaking", "transformative",
]
BANNED_PATTERNS = [
    (r"\bnot (?:just|only|merely) [^.;:\n]{1,80}?,? but\b", "binary contrast (not just X, but Y)"),
    (r"\b(?:it|this|that) ?(?:is|'s) not [^.;:\n]{1,60}?, (?:it|this|that) ?(?:is|'s)\b",
     "binary contrast (it is not X, it is Y)"),
    (r"\b(?:isn't|aren't) [^.;:\n]{1,60}?, (?:it|they) ?(?:is|are|'s|'re)\b",
     "binary contrast (isn't X, it's Y)"),
    (r"(?:^|\. )here's the thing\b", "throat-clearing opener"),
    (r"(?:^|\. )let's (?:be honest|dive|break it down)\b", "throat-clearing opener"),
    (r"\bit's worth noting\b", "filler"),
    (r"\bat the end of the day\b", "filler"),
    (r"\bin today's [a-z -]*world\b", "filler"),
    (r"\bharness the power\b", "buzzword phrase"),
    (r"\bnavigate the complexit", "buzzword phrase"),
]

# Local home folders on macOS, Linux and Windows.
PRIVATE_PATH = re.compile(r"(?:/(?:Users|home)/|[A-Za-z]:\\Users\\)[A-Za-z0-9._-]+")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
ALLOWED_EMAIL_DOMAINS = re.compile(r"(?:^|\.)(?:example|example\.com|example\.org|example\.net|"
                                   r"users\.noreply\.github\.com)$")
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
ALLOWED_IP_PREFIXES = ("127.", "0.0.0.0", "192.0.2.", "198.51.100.", "203.0.113.")
TOKENS = [
    (r"gh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"github_pat_[A-Za-z0-9_]{20,}", "GitHub fine-grained token"),
    (r"sk-(?:ant-)?[A-Za-z0-9_-]{20,}", "API secret key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"xox[abprs]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"AIza[0-9A-Za-z_-]{35}", "Google API key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
]
AI_ATTRIBUTION = [
    (r"(?i)co-authored-by:[^\n]*(?:claude|anthropic|openai|chatgpt|copilot|gemini|"
     r"antigravity|cursor|devin|codex)", "AI Co-Authored-By trailer"),
    (r"(?i)generated with \[?(?:claude|chatgpt|copilot|gemini|cursor)", "Generated with line"),
]
# File and folder names that hold working state or agent instructions, at any depth.
FORBIDDEN_NAMES = ["IN-FLIGHT.md", "handoffs", "AGENTS.md", "CLAUDE.md", "GEMINI.md",
                   ".cursorrules"]

GLOBAL_FLAGS = {"help", "json", "pairing-code", "environment"}


class Report:
    def __init__(self):
        self.sections = []

    def section(self, name, checked, problems):
        self.sections.append((name, checked, problems))

    def print(self):
        total = 0
        for name, checked, problems in self.sections:
            total += len(problems)
            print(f"[{name}] {checked}, {len(problems)} problem(s)")
            for p in problems:
                print(f"  - {p}")
        print(f"TOTAL: {total} problem(s)")
        return total


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def repo_files():
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True).stdout
        files = [ROOT / line for line in out.splitlines() if line]
    except (OSError, subprocess.CalledProcessError):
        files = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
    return sorted(p for p in files if p.is_file())


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def markdown_files():
    return [p for p in repo_files() if p.suffix == ".md"]


def strip_code(text, keep_lines=True):
    """Blank fenced blocks and inline code so prose checks see prose only."""
    out = []
    fence = None
    for line in text.split("\n"):
        stripped = line.lstrip()
        m = re.match(r"(`{3,}|~{3,})", stripped)
        if fence:
            if m and stripped.startswith(fence):
                fence = None
            out.append("")
            continue
        if m:
            fence = m.group(1)
            out.append("")
            continue
        out.append(re.sub(r"`+[^`]*`+", "", line))
    return "\n".join(out) if keep_lines else " ".join(out)


# ---------------------------------------------------------------- 1. skills

def parse_front_matter(text):
    if not text.startswith("---\n"):
        return None, "missing opening --- line"
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, "missing closing --- line"
    data = {}
    for n, line in enumerate(text[4:end].split("\n"), start=2):
        if not line.strip():
            continue
        m = re.match(r"([A-Za-z0-9_-]+):(?: (.*))?$", line)
        if not m:
            return None, f"line {n} is not a 'key: value' pair: {line!r}"
        key, value = m.group(1), (m.group(2) or "").strip()
        if key in data:
            return None, f"duplicate key {key!r}"
        if value[:1] in ("'", '"'):
            if len(value) < 2 or value[-1] != value[0]:
                return None, f"unbalanced quotes in {key!r}"
            value = value[1:-1]
        elif value.startswith(("|", ">", "[", "{")):
            return None, f"{key!r} uses YAML syntax this check does not accept"
        data[key] = value
    return data, None


def skill_tiers():
    tiers = {}
    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        m = re.search(r"^\*\*Tier: (\w+)\.\*\*", read_text(skill_md) or "", re.M)
        tiers[skill_md.parent.name] = m.group(1) if m else None
    return tiers


def check_skills(report):
    problems = []
    skill_dirs = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    present = {d.name for d in skill_dirs}
    for name in sorted(present - set(PUBLIC_SKILLS)):
        problems.append(f"skills/{name}: not in the public skill allowlist")
    for name in sorted(set(PUBLIC_SKILLS) - present):
        problems.append(f"skills/{name}: allowlisted skill is missing")
    for d in skill_dirs:
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            problems.append(f"skills/{d.name}: no SKILL.md")
            continue
        text = read_text(skill_md) or ""
        data, err = parse_front_matter(text)
        where = rel(skill_md)
        if err:
            problems.append(f"{where}: front matter: {err}")
            continue
        extra = sorted(set(data) - set(ALLOWED_FRONT_MATTER_KEYS))
        if extra:
            problems.append(f"{where}: unexpected front matter keys {extra}")
        if data.get("name") != d.name:
            problems.append(f"{where}: name {data.get('name')!r} differs from folder {d.name!r}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", data.get("name") or "") or \
                len(data.get("name") or "") > 64:
            problems.append(f"{where}: name is not lower-case words joined by hyphens (max 64)")
        desc = data.get("description", "")
        if not desc:
            problems.append(f"{where}: empty or missing description")
        elif len(desc) > 1024:
            problems.append(f"{where}: description longer than 1024 characters")
        tier = re.search(r"^\*\*Tier: (\w+)\.\*\*", text, re.M)
        if not tier or tier.group(1) not in TIERS:
            problems.append(f"{where}: no '**Tier: Basic.**' or '**Tier: Advanced.**' line")
    version = re.compile(rf"(?i)\borca(?: cli)?\s+v?{SEMVER}\b|\b1\.4\.\d+\b")
    scanned = 0
    for base in ("skills", "examples"):
        for p in sorted((ROOT / base).rglob("*")):
            if not p.is_file():
                continue
            scanned += 1
            for n, line in enumerate((read_text(p) or "").split("\n"), 1):
                if version.search(line):
                    problems.append(f"{rel(p)}:{n}: hardcoded Orca version: {line.strip()}")
    report.section("skills", f"{len(skill_dirs)} skills, {scanned} files scanned for versions",
                   problems)


# ---------------------------------------------------------------- 2. links

def slugify(heading):
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = text.replace("`", "").replace("*", "")
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path, cache={}):
    if path not in cache:
        found = set()
        counts = {}
        for line in strip_code_fences_only(read_text(path) or "").split("\n"):
            m = re.match(r"(#{1,6})\s+(.*?)\s*#*\s*$", line)
            if not m:
                continue
            slug = slugify(m.group(2))
            n = counts.get(slug, 0)
            counts[slug] = n + 1
            found.add(slug if n == 0 else f"{slug}-{n}")
        cache[path] = found
    return cache[path]


def strip_code_fences_only(text):
    out, fence = [], None
    for line in text.split("\n"):
        stripped = line.lstrip()
        m = re.match(r"(`{3,}|~{3,})", stripped)
        if fence:
            if m and stripped.startswith(fence):
                fence = None
            out.append("")
        elif m:
            fence = m.group(1)
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


LINK = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+.*)?$", re.M)


def check_links(report):
    problems = []
    count = 0
    files = markdown_files()
    for md in files:
        text = read_text(md) or ""
        prose = strip_code(text)
        targets = [(m.group(1), prose[:m.start()].count("\n") + 1) for m in LINK.finditer(prose)]
        targets += [(m.group(1), prose[:m.start()].count("\n") + 1)
                    for m in REF_DEF.finditer(prose)]
        for target, line in targets:
            if re.match(r"[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            count += 1
            path_part, _, anchor = target.partition("#")
            dest = md if not path_part else (md.parent / path_part).resolve()
            where = f"{rel(md)}:{line}"
            if not dest.exists():
                problems.append(f"{where}: broken link {target}")
                continue
            if ROOT not in dest.parents and dest != ROOT:
                problems.append(f"{where}: link leaves the repository: {target}")
                continue
            if anchor:
                if dest.suffix != ".md":
                    problems.append(f"{where}: anchor on a non-Markdown target {target}")
                elif anchor not in anchors(dest):
                    problems.append(f"{where}: no heading for anchor {target}")
    report.section("links", f"{count} relative links in {len(files)} Markdown files", problems)


# ---------------------------------------------------------------- 3. README

def section_text(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def readme_version():
    m = re.search(rf"badge/Orca%20CLI-({SEMVER})-", read_text(ROOT / "README.md") or "")
    return m.group(1) if m else None


def check_readme(report):
    problems = []
    text = read_text(ROOT / "README.md") or ""
    tiers = skill_tiers()
    basic = sorted(s for s, t in tiers.items() if t == "Basic")
    advanced = sorted(s for s, t in tiers.items() if t == "Advanced")

    badge = readme_version()
    compat = re.findall(rf"\bOrca ({SEMVER})\b", section_text(text, "Compatibility"))
    if not badge:
        problems.append("README.md: no Orca CLI badge with a version")
    if len(set(compat)) != 1:
        problems.append(f"README.md: Compatibility must name one Orca version, found {compat}")
    elif badge and compat[0] != badge:
        problems.append(f"README.md: badge says {badge}, Compatibility says {compat[0]}")
    others = set(re.findall(rf"\b1\.4\.\d+\b", text)) - {badge}
    if others:
        problems.append(f"README.md: other Orca versions mentioned: {sorted(others)}")

    for label, names in (("Basic", basic), ("Advanced", advanced)):
        m = re.search(rf"badge/{label}%20skills-(\d+)-", text)
        if not m:
            problems.append(f"README.md: no {label} skills badge")
        elif int(m.group(1)) != len(names):
            problems.append(f"README.md: {label} badge says {m.group(1)}, "
                            f"skills/ has {len(names)} {label} skills")
        table = section_text(text, f"{label} skills")
        listed = sorted(re.findall(r"^\| \[`([a-z0-9-]+)`\]\(skills/", table, re.M))
        if listed != names:
            problems.append(f"README.md: {label} skills table lists {listed}, expected {names}")

    m = re.search(r"^BASIC=\(([^)]*)\)", text, re.M)
    if not m or sorted(m.group(1).split()) != basic:
        problems.append(f"README.md: BASIC array does not match the Basic skills {basic}")
    m = re.search(r"^ADVANCED=\(\"\$\{BASIC\[@\]\}\"([^)]*)\)", text, re.M | re.S)
    if not m or sorted(m.group(1).split()) != advanced:
        problems.append(f"README.md: ADVANCED array does not match the Advanced skills {advanced}")
    m = re.search(r"for s in ([a-z0-9 -]+); do\n\s+ln -s", section_text(text, "Quick start"))
    if not m or sorted(m.group(1).split()) != basic:
        problems.append("README.md: Quick start loop does not list the Basic skills")
    missing = [s for s in tiers if tiers[s] is None]
    if missing:
        problems.append(f"skills without a tier: {missing}")
    report.section("readme", f"version {badge}, {len(basic)} Basic and {len(advanced)} "
                   f"Advanced skills", problems)


# ---------------------------------------------------------------- 4. prose

def check_prose(report):
    problems = []
    files = [p for p in markdown_files()]
    words = re.compile(r"(?i)\b(?:" + "|".join(re.escape(w) for w in BANNED_WORDS) + r")\b")
    patterns = [(re.compile(p, re.I | re.M), why) for p, why in BANNED_PATTERNS]
    for md in files:
        text = read_text(md) or ""
        for n, line in enumerate(text.split("\n"), 1):
            for ch, name in DASHES.items():
                if ch in line:
                    problems.append(f"{rel(md)}:{n}: {name}")
        prose = strip_code(text)
        for n, line in enumerate(prose.split("\n"), 1):
            line = re.sub(r"\]\([^)]*\)", "]", line)
            for m in words.finditer(line):
                problems.append(f"{rel(md)}:{n}: banned word {m.group(0)!r}")
            for rx, why in patterns:
                for m in rx.finditer(line):
                    problems.append(f"{rel(md)}:{n}: {why}: {m.group(0)!r}")
    script_dashes = [n for n, line in enumerate((read_text(SELF) or "").split("\n"), 1)
                     if any(ch in line for ch in DASHES)]
    for n in script_dashes:
        problems.append(f"{rel(SELF)}:{n}: literal dash character")
    report.section("prose", f"{len(files)} Markdown files", problems)


# ---------------------------------------------------------------- 5. privacy

def check_privacy(report):
    problems = []
    files = repo_files()
    scanned = 0
    for p in files:
        text = read_text(p)
        if text is None:
            continue
        scanned += 1
        for n, line in enumerate(text.split("\n"), 1):
            where = f"{rel(p)}:{n}"
            for m in PRIVATE_PATH.finditer(line):
                problems.append(f"{where}: private path {m.group(0)}")
            for m in EMAIL.finditer(line):
                domain = m.group(0).rsplit("@", 1)[1].lower()
                if not ALLOWED_EMAIL_DOMAINS.search(domain) and m.group(0) != "git@github.com":
                    problems.append(f"{where}: email address {m.group(0)}")
            for m in IPV4.finditer(line):
                ip = m.group(0)
                if all(int(o) <= 255 for o in ip.split(".")) and \
                        not ip.startswith(ALLOWED_IP_PREFIXES):
                    problems.append(f"{where}: IP address {ip}")
            for rx, why in TOKENS:
                if re.search(rx, line) and p != SELF:
                    problems.append(f"{where}: {why}")
            if p != SELF:
                for rx, why in AI_ATTRIBUTION:
                    if re.search(rx, line):
                        problems.append(f"{where}: {why}")
    for f in files:
        hits = [part for part in Path(rel(f)).parts if part in FORBIDDEN_NAMES]
        if hits:
            problems.append(f"{rel(f)}: {hits[0]} must not exist in this public repository")
    try:
        log = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%H%n%B"],
                             capture_output=True, text=True, check=True).stdout
        commits = log.count("\n") and len(re.findall(r"^[0-9a-f]{40}$", log, re.M))
        for rx, why in AI_ATTRIBUTION:
            for m in re.finditer(rx, log):
                problems.append(f"git history: {why}: {m.group(0)}")
    except (OSError, subprocess.CalledProcessError):
        commits = 0
        problems.append("git history could not be read")
    report.section("privacy", f"{scanned} text files, {commits} commit messages", problems)


# ---------------------------------------------------------------- --check-cli

def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                           stdin=subprocess.DEVNULL)
        return r.returncode, r.stdout + r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def orca_commands(text):
    """Yield (line, command text) for each orca command in fenced blocks and inline code."""
    fence = None
    pending, start = "", 0
    lines = text.split("\n")
    for n, line in enumerate(lines, 1):
        stripped = line.strip()
        m = re.match(r"(`{3,}|~{3,})", stripped)
        if fence:
            if m and stripped.startswith(fence):
                fence = None
                continue
            if pending:
                pending += " " + stripped
            elif re.match(r"(?:\$ )?orca(?:\s|$)", stripped) or " orca " in f" {stripped}":
                pending, start = stripped, n
            else:
                continue
            if pending.endswith("\\"):
                pending = pending[:-1].rstrip()
                continue
            for seg in segments(pending):
                yield start, seg
            pending = ""
            continue
        if m:
            fence = m.group(1)
            continue
        for span in re.findall(r"`([^`]+)`", line):
            for seg in segments(span):
                yield n, seg


def segments(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";|&")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    current = []
    for tok in tokens + [";"]:
        if tok and set(tok) <= set(";|&"):
            if current and current[0] in ("orca", "$orca"):
                yield current[1:]
            current = []
        elif tok.startswith("#") and not current:
            break
        else:
            if not current and tok == "$":
                continue
            current.append(tok)


class Cli:
    def __init__(self):
        code, out = run(["orca", "agent-context", "--json"])
        if code != 0:
            raise SystemExit(f"orca agent-context --json failed: {out.strip()[:300]}")
        data = json.loads(out)
        self.specs = {}
        for c in data["commands"]:
            flags = set(c.get("flags", []))
            for path in [c["path"]] + c.get("aliases", []):
                self.specs[tuple(path)] = flags
        self.groups = {path[:i] for path in self.specs for i in range(1, len(path))}
        self.help_cache = {}

    def help(self, path):
        if path not in self.help_cache:
            code, out = run(["orca", *path, "--help"])
            first = out.strip().split("\n", 1)[0].strip()
            if code != 0 or first != "orca " + " ".join(path):
                self.help_cache[path] = None
            else:
                flags = set(re.findall(r"(?m)^\s+--([a-z0-9][a-z0-9-]*)", out))
                usage = re.search(r"(?m)^Usage: (.*)$", out)
                if usage:
                    flags |= set(re.findall(r"--([a-z0-9][a-z0-9-]*)", usage.group(1)))
                is_group = bool(re.search(r"(?m)^Commands:", out))
                self.help_cache[path] = (flags | GLOBAL_FLAGS, is_group)
        return self.help_cache[path]

    def resolve(self, words):
        """Return (path, flags, source) for the longest known command prefix of words."""
        for i in range(len(words), 0, -1):
            path = tuple(words[:i])
            if path in self.specs:
                return path, self.specs[path], "agent-context"
        for i in range(len(words), 0, -1):
            path = tuple(words[:i])
            h = self.help(path)
            if h and not h[1]:
                return path, h[0], "help"
        for i in range(len(words), 0, -1):
            path = tuple(words[:i])
            if path in self.groups or (self.help(path) or (None, False))[1]:
                return path, GLOBAL_FLAGS, "group"
        return None, None, None


def check_cli(report):
    problems = []
    cli = Cli()
    code, out = run(["orca", "--version"])
    host = out.strip() if code == 0 else None
    readme = readme_version()
    if host != readme:
        problems.append(f"orca --version is {host}, README.md records {readme}")
    seen = set()
    commands = 0
    via = {"agent-context": 0, "help": 0, "group": 0}
    skipped = 0
    for md in markdown_files():
        for line, tokens in orca_commands(read_text(md) or ""):
            where = f"{rel(md)}:{line}"
            if not tokens:
                continue
            words = []
            for tok in tokens:
                if tok.startswith("-") or not re.fullmatch(r"[a-z][a-z0-9-]*", tok):
                    break
                words.append(tok)
            if tokens[0].startswith("<"):
                skipped += 1
                continue
            flags = {re.match(r"--([A-Za-z0-9-]+)", t).group(1)
                     for t in tokens if re.match(r"--[A-Za-z0-9]", t)}
            key = (tuple(words), tuple(sorted(flags)))
            commands += 1
            if not words:
                bad = flags - {"version", "help"}
                if bad:
                    problems.append(f"{where}: unknown top-level flags {sorted(bad)}")
                continue
            path, known, source = cli.resolve(words)
            if path is None:
                problems.append(f"{where}: unknown command 'orca {' '.join(words)}'")
                continue
            via[source] += 1
            bad = flags - known
            if source == "group":
                bad = flags - {"help"}
                if bad or len(words) > len(path):
                    problems.append(f"{where}: 'orca {' '.join(words)}' is not a command "
                                    f"('orca {' '.join(path)}' is a group)")
                    continue
            if bad and key not in seen:
                problems.append(f"{where}: 'orca {' '.join(path)}' has no flag(s) "
                                f"{', '.join('--' + b for b in sorted(bad))}")
            seen.add(key)
    report.section("cli", f"orca {host}: {commands} commands checked ({via['agent-context']} "
                   f"via agent-context, {via['help']} via --help, {via['group']} groups), "
                   f"{skipped} placeholders skipped", problems)


def main():
    parser = argparse.ArgumentParser(description="Check this repository's skills and docs.")
    parser.add_argument("--check-cli", action="store_true",
                        help="also check every orca command and flag against this host")
    args = parser.parse_args()
    os.chdir(ROOT)
    report = Report()
    check_skills(report)
    check_links(report)
    check_readme(report)
    check_prose(report)
    check_privacy(report)
    if args.check_cli:
        check_cli(report)
    return 1 if report.print() else 0


if __name__ == "__main__":
    sys.exit(main())
