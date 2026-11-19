#!/usr/bin/env python3
"""Recense les skills et agents des dépôts listés dans config.json, les classe
par but, repère les doublons et les nouveautés, et écrit board.json.

Usage : python3 board/build_board.py [--root DOSSIER_DES_DEPOTS]
Sans --root, le dossier parent de ce dépôt est utilisé.
"""
import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Catégories : (id, libellé, mots-clés). Un mot-clé dans le NOM pèse 3, dans la description 1.
CATEGORIES = [
    ("security", "Sécurité & conformité", [
        "security", "secure", "owasp", "hipaa", "phi", "compliance", "guard", "sanitiz", "bounty",
        "vulnerab", "safety", "gateguard", "perimeter", "osint"]),
    ("review", "Revue de code & qualité", [
        "review", "reviewer", "quality", "lint", "refactor", "clean", "simplif", "code-health",
        "codehealth", "standards", "audit", "silent-failure", "comment", "dead code", "necromancer",
        "plankton", "conventional-commit", "explore-codebase", "codebase", "onboarding", "code-tour",
        "graph", "debug", "bug", "fix", "root cause"]),
    ("test", "Tests & vérification", [
        "test", "tdd", "e2e", "playwright", "vitest", "qa", "verification", "verify", "eval",
        "benchmark", "regression", "canary", "smoke"]),
    ("lang", "Langages & frameworks", [
        "python", "golang", "go-", "rust", "java", "kotlin", "swift", "swiftui", "typescript",
        "react", "vue", "angular", "nextjs", "nuxt", "django", "fastapi", "laravel", "rails",
        "springboot", "spring", "quarkus", "flutter", "dart", "csharp", "dotnet", "fsharp", "cpp",
        "perl", "php", "ruby", "nestjs", "bun", "vite", "godot", "gdscript", "jpa", "mybatis",
        "prisma", "drizzle", "ktor", "compose", "android", "ios", "build-resolver", "build error",
        "harmonyos", "pytorch", "react-native", "tinystruct", "exposed"]),
    ("archi", "Architecture, API & données backend", [
        "architect", "architecture", "api", "rest", "graphql", "openapi", "backend", "database",
        "postgres", "mysql", "redis", "clickhouse", "sql", "migration", "schema", "microservice",
        "hexagonal", "caching", "cache", "queue", "job", "websocket", "streaming", "realtime",
        "real-time", "error-handling", "auth", "oauth", "contract-first", "monorepo", "dependency",
        "latency", "event"]),
    ("ops", "DevOps, infra & réseau", [
        "devops", "docker", "kubernetes", "terraform", "deploy", "deployment", "ci", "github-actions",
        "pipeline-builder", "vercel", "cloudflare", "supabase", "network", "homelab", "vlan",
        "wireguard", "pihole", "bgp", "cisco", "netmiko", "sre", "reliability", "observability",
        "logging", "monitoring", "git", "port", "flox", "terminal", "uncloud", "infra", "server"]),
    ("ai", "IA, LLM & agents", [
        "agent", "agentic", "llm", "prompt", "rag", "embedding", "mcp", "skill", "harness",
        "orchestrat", "loop", "council", "claude", "model", "token", "context", "memory",
        "retrieval", "inference", "training", "ml", "machine learning", "ai-", "ai ", "gan",
        "subagent", "workflow", "ecc", "plan", "planner", "planning", "task", "routing", "router",
        "cost", "vector", "weaver", "fine-tun"]),
    ("video", "Vidéo, audio & médias", [
        "video", "hyperframes", "remotion", "motion", "caption", "subtitle", "audio", "sound",
        "voice", "music", "speech", "media", "watch", "transcri", "frame", "slideshow", "manim",
        "seam", "cursor", "cut-the-curve", "changelog-video", "figma", "fal-ai", "visualization",
        "milkdrop", "shader", "animation", "film", "footage", "render"]),
    ("design", "Design, UI & frontend", [
        "design", "ui", "ux", "frontend", "css", "web-design", "typography", "color", "palette",
        "accessib", "a11y", "wcag", "dark-mode", "glass", "brutalist", "win31", "windows-",
        "vaporwave", "component", "tailwind", "pixel-art", "icon", "layout", "collage", "photo",
        "interface", "21st", "taste", "brand", "mobile", "pwa", "native-app", "interior", "landscap",
        "decorat"]),
    ("data", "Données, visualisation & cartes", [
        "data", "dashboard", "chart", "viz", "diagram", "mermaid", "map", "geospatial", "scrap",
        "analytics", "metrics", "reactflow", "infographic", "computer vision", "vision", "yolo",
        "drone", "clip", "recsys", "scientific", "pubmed", "openalex", "throughput"]),
    ("content", "Recherche, docs & contenu", [
        "research", "doc", "docs", "documentation", "writer", "writing", "article", "content",
        "seo", "marketing", "social", "publish", "crosspost", "email", "summar", "archiv", "librar",
        "scout", "cartograph", "liaison", "knowledge", "search", "pdf", "mdx", "i18n", "translat",
        "localization", "legal", "x-api", "newsletter", "campaign"]),
    ("business", "Business, carrière & ops", [
        "career", "cv", "resume", "interview", "job", "hiring", "investor", "market", "finance",
        "billing", "pricing", "monetiz", "entrepreneur", "competitive", "product", "launch",
        "customer", "logistics", "inventory", "procurement", "trade", "customs", "agreement",
        "esign", "lead", "growth", "jira", "project", "team", "boss", "manager", "operations",
        "-ops", "prediction-market", "defi", "x402", "payment", "energy", "carrier", "production"]),
    ("life", "Vie perso & bien-être", [
        "adhd", "grief", "crisis", "sober", "addict", "rehab", "partner", "hinge", "dating",
        "wedding", "pet", "memorial", "jungian", "psycholog", "wisdom", "coach", "personal",
        "estate", "hrv", "alexithymia", "health", "clinical", "mental", "therapy", "panic",
        "knot", "munger", "emotional", "relationship"]),
]
OTHER = ("other", "Autres", [])

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)


def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER.match(text)
    out = {}
    if not m:
        return out
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        kv = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if kv and kv.group(1) in ("name", "description"):
            key, val = kv.group(1), kv.group(2).strip()
            if val in ("|", ">", "|-", ">-", ""):
                buf = []
                i += 1
                while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                    buf.append(lines[i].strip())
                    i += 1
                val = " ".join(b for b in buf if b)
                out[key] = val
                continue
            out[key] = val.strip("\"'")
        i += 1
    return out


def first_paragraph(text: str) -> str:
    body = FRONTMATTER.sub("", text, count=1)
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        if b and not b.startswith("#") and not b.startswith("```") and not b.startswith("<"):
            return re.sub(r"\s+", " ", b)[:300]
    return ""


# Les éléments d'un dépôt penchent vers la catégorie de sa famille (+2).
FAMILY_BIAS = {"Vidéo": "video"}


def classify(name: str, desc: str, kind: str, bias: str = ""):
    n = name.lower()
    d = desc.lower()
    scores = {}
    for cid, _, kws in CATEGORIES:
        s = 0
        for kw in kws:
            if kw in n:
                s += 3
            if re.search(r"(?<![a-z])" + re.escape(kw), d):
                s += 1
        if s:
            scores[cid] = s
    if bias and bias in scores:
        scores[bias] += 2
    if not scores:
        return OTHER[0], []
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    best = ranked[0][0]
    also = [c for c, s in ranked[1:3] if s >= max(2, ranked[0][1] - 1)]
    return best, also


def collect(root: Path, repo: str, rel: str, kind: str):
    base = root / rel
    if not base.is_dir():
        return []
    items = []
    if kind == "skill":
        files = [p for p in base.glob("*/SKILL.md")]
    else:
        # agents/<nom>.md (ECC) ou agents/<nom>/AGENT.md ; on ignore README.md, FOUNDING_COUNCIL.md…
        files = [p for p in base.glob("*.md") if p.stem != p.stem.upper()]
        files += list(base.glob("*/AGENT.md"))
    for f in sorted(files):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = parse_frontmatter(text)
        name = fm.get("name") or (f.parent.name if f.name in ("SKILL.md", "AGENT.md") else f.stem)
        desc = fm.get("description") or first_paragraph(text)
        items.append({
            "name": name.strip(),
            "kind": kind,
            "repo": repo,
            "path": str(f.relative_to(root)),
            "description": re.sub(r"\s+", " ", desc).strip()[:400],
        })
    return items


def git(repo_dir: Path, *args: str) -> str:
    """Lance git sans shell ; renvoie '' en cas d'échec."""
    try:
        return subprocess.run(["git", "-C", str(repo_dir), *args], capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=60, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def collect_branches(root: Path, repo: str, dirs: list):
    """Skills présents sur les autres branches distantes (origin/*) du dépôt, sans checkout."""
    repo_dir = root / repo
    if not (repo_dir / ".git").exists():
        return []
    current = git(repo_dir, "rev-parse", "--abbrev-ref", "HEAD").strip()
    refs = [r for r in git(repo_dir, "for-each-ref", "--format=%(refname:short)",
                           "refs/remotes/origin").split() if r != "origin/HEAD" and r != "origin"]
    items = []
    for ref in refs:
        branch = ref.split("/", 1)[1]
        if branch == current:
            continue
        listing = git(repo_dir, "ls-tree", "-r", "--name-only", ref, "--", *dirs)
        for path in listing.splitlines():
            if not any(re.fullmatch(re.escape(d) + r"/[^/]+/SKILL\.md", path) for d in dirs):
                continue
            text = git(repo_dir, "show", f"{ref}:{path}")
            if not text:
                continue
            fm = parse_frontmatter(text)
            name = (fm.get("name") or path.split("/")[-2]).strip()
            desc = fm.get("description") or first_paragraph(text)
            items.append({
                "name": name, "kind": "skill", "repo": repo, "branch": branch,
                "path": f"{repo}/{path} (branche {branch})",
                "description": re.sub(r"\s+", " ", desc).strip()[:400],
            })
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE.parent.parent))
    ap.add_argument("--out", default=str(HERE / "board.json"))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    out_path = Path(args.out)

    previous = {}
    if out_path.exists():
        try:
            prev = json.loads(out_path.read_text(encoding="utf-8"))
            previous = {(i["kind"], i["name"]): i for i in prev.get("items", [])}
        except (OSError, ValueError, KeyError):
            previous = {}
    today = dt.date.today().isoformat()

    raw = []
    repos = []
    branch_items = []
    for repo, rc in cfg["repos"].items():
        present = (root / repo).is_dir()
        found = []
        for rel in rc.get("skills", []):
            found += collect(root, repo, rel, "skill")
        for rel in rc.get("agents", []):
            found += collect(root, repo, rel, "agent")
        raw += found
        if cfg.get("scan_branches", True):
            dirs = [p.split("/", 1)[1] for p in rc.get("skills", []) if "/" in p]
            dirs += [d for d in cfg.get("branch_skill_dirs", []) if d not in dirs]
            branch_items.extend(collect_branches(root, repo, dirs))
        repos.append({
            "name": repo, "goal": rc["goal"], "family": rc["family"], "present": present,
            "skills": sum(1 for i in found if i["kind"] == "skill"),
            "agents": sum(1 for i in found if i["kind"] == "agent"),
        })

    # Un skill vu seulement sur une autre branche n'entre que s'il n'existe nulle part ailleurs
    # (sinon une vieille branche ferait revenir des copies déjà supprimées).
    known = {(i["kind"], i["name"]) for i in raw}
    seen = set()
    for it in branch_items:
        key = (it["kind"], it["name"])
        if key in known or key in seen:
            continue
        seen.add(key)
        raw.append(it)
        for r in repos:
            if r["name"] == it["repo"]:
                r["skills"] += 1

    # Fusion des doublons (même type + même nom) : une seule carte, avec la liste des dépôts.
    merged = {}
    for it in raw:
        key = (it["kind"], it["name"])
        if key not in merged:
            merged[key] = dict(it, repos=[it["repo"]], paths=[it["path"]])
        else:
            m = merged[key]
            if it["repo"] not in m["repos"]:
                m["repos"].append(it["repo"])
            m["paths"].append(it["path"])
            if len(it["description"]) > len(m["description"]):
                m["description"] = it["description"]

    items = []
    for key, it in merged.items():
        fams = {cfg["repos"][r]["family"] for r in it["repos"] if r in cfg["repos"]}
        bias = next((FAMILY_BIAS[f] for f in fams if f in FAMILY_BIAS), "")
        cat, also = classify(it["name"], it["description"], it["kind"], bias)
        prev = previous.get(key)
        first_seen = prev.get("first_seen", today) if prev else today
        items.append({
            "name": it["name"], "kind": it["kind"], "category": cat, "also": also,
            "repos": it["repos"], "path": it["paths"][0], "description": it["description"],
            "duplicate": len(it["repos"]) > 1, "first_seen": first_seen,
            "branch": it.get("branch", ""),
            "new": prev is None and bool(previous),
        })
    items.sort(key=lambda i: (i["category"], i["kind"], i["name"].lower()))

    removed = [
        {"name": k[1], "kind": k[0], "repos": v.get("repos", [])}
        for k, v in previous.items() if k not in merged
    ]

    board = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "categories": [{"id": c, "label": l} for c, l, _ in CATEGORIES] + [
            {"id": OTHER[0], "label": OTHER[1]}],
        "repos": repos,
        "items": items,
        "removed": removed,
        "stats": {
            "skills": sum(1 for i in items if i["kind"] == "skill"),
            "agents": sum(1 for i in items if i["kind"] == "agent"),
            "duplicates": sum(1 for i in items if i["duplicate"]),
            "new": sum(1 for i in items if i["new"]),
        },
    }
    out_path.write_text(json.dumps(board, ensure_ascii=False, indent=1), encoding="utf-8")

    # Fichiers « à plat » pour le board (une ligne = un skill/agent, une ligne = un dépôt).
    labels = {c["id"]: c["label"] for c in board["categories"]}
    flat = [{
        "name": i["name"], "type": "Agent" if i["kind"] == "agent" else "Skill",
        "category": labels[i["category"]], "also": ", ".join(labels[a] for a in i["also"]),
        "repos": ", ".join(i["repos"]), "duplicate": "oui" if i["duplicate"] else "non",
        "new": "oui" if i["new"] else "non", "first_seen": i["first_seen"],
        "description": i["description"], "path": i["path"], "branch": i.get("branch", ""),
    } for i in items]
    (out_path.parent / "items.json").write_text(
        json.dumps(flat, ensure_ascii=False), encoding="utf-8")
    (out_path.parent / "repos.json").write_text(
        json.dumps(repos, ensure_ascii=False), encoding="utf-8")
    s = board["stats"]
    print(f"{s['skills']} skills, {s['agents']} agents, {s['duplicates']} doublons, "
          f"{s['new']} nouveaux, {len(removed)} retirés -> {out_path}")


if __name__ == "__main__":
    main()
