#!/usr/bin/env python3
"""Consulta de solo lectura de la base de conocimiento docs/investigaciones/.

Sin dependencias externas. Nunca escribe archivos.

Uso:
  kb.py list                      Lista las investigaciones (frontmatter resumido)
  kb.py search TERM [TERM...]     Busca en INDEX.md y en el frontmatter (título, tema, tags, módulos)
  kb.py show SLUG                 Frontmatter + encabezados de un documento (sin cuerpo)
  kb.py stale [--days N]          Investigaciones con last_verified > N días (180 por defecto) o estado dudoso
  kb.py check                     Valida frontmatter, secciones obligatorias, índice y enlaces

Opción global: --root RUTA (por defecto: raíz git o directorio actual).
Códigos de salida: 0 ok · 1 sin resultados / problemas detectados · 2 error de uso.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

REQUIRED_FIELDS = ["title", "topic", "status", "created", "updated",
                   "last_verified", "tags", "related_modules", "source_count"]
VALID_STATUS = {"borrador", "vigente", "parcialmente-verificada",
                "requiere-actualizacion", "obsoleta"}
REQUIRED_SECTIONS = [
    "Resumen ejecutivo", "Objetivo y preguntas de investigación",
    "Contexto y relación con SIGPI", "Alcance y metodología", "Hallazgos verificados",
    "Análisis técnico y conceptual", "Comparación de alternativas",
    "Limitaciones, contradicciones e incertidumbre",
    "Implicaciones arquitectónicas y funcionales", "Recomendaciones justificadas",
    "Opciones concretas de aplicación al proyecto",
    "Plan de validación o implementación sugerida", "Preguntas abiertas",
    "Fuentes y referencias verificables", "Historial de revisiones",
]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SKIP = {"INDEX.md", "README.md"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def find_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except Exception:
        return Path.cwd()


def parse_frontmatter(text: str) -> tuple[dict, str | None]:
    """Parser mínimo de YAML plano: claves escalares y listas en línea [a, b] o con guiones."""
    if not text.startswith("---"):
        return {}, "sin frontmatter"
    lines = text.splitlines()
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, "frontmatter sin cierre ---"
    data: dict = {}
    key = None
    for raw in lines[1:end]:
        line = re.sub(r"\s+#.*$", "", raw).rstrip()
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                data[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            elif val == "":
                data[key] = []
            else:
                data[key] = val.strip("'\"")
        elif key and re.match(r"^\s+-\s+", line):
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(re.sub(r"^\s+-\s+", "", line).strip("'\""))
        else:
            return data, f"línea no reconocida: {raw!r}"
    return data, None


def docs(root: Path) -> list[Path]:
    d = root / "docs" / "investigaciones"
    return sorted(p for p in d.glob("*.md") if p.name not in SKIP) if d.is_dir() else []


def load(p: Path) -> tuple[dict, str, str | None]:
    text = p.read_text(encoding="utf-8")
    fm, err = parse_frontmatter(text)
    return fm, text, err


def as_list(v) -> list[str]:
    return v if isinstance(v, list) else ([v] if v else [])


def cmd_list(root: Path, _a) -> int:
    ds = docs(root)
    if not ds:
        print("No hay investigaciones en docs/investigaciones/.")
        return 1
    for p in ds:
        fm, _, _ = load(p)
        print(f"{p.stem}\t{fm.get('status', '?')}\tverificada={fm.get('last_verified', '?')}"
              f"\t{fm.get('title', '?')}\tmódulos={','.join(as_list(fm.get('related_modules')))}")
    return 0


def cmd_search(root: Path, a) -> int:
    terms = [norm(t) for t in a.terms]
    hits = 0
    idx = root / "docs" / "investigaciones" / "INDEX.md"
    if idx.exists():
        for line in idx.read_text(encoding="utf-8").splitlines():
            if line.startswith("|") and not line.startswith("|---") and any(t in norm(line) for t in terms):
                print(f"[INDEX] {line}")
                hits += 1
    for p in docs(root):
        fm, _, _ = load(p)
        hay = " ".join([p.stem, str(fm.get("title", "")), str(fm.get("topic", "")),
                        *as_list(fm.get("tags")), *as_list(fm.get("related_modules"))])
        matched = [t for t in terms if t in norm(hay)]
        if matched:
            print(f"[DOC] docs/investigaciones/{p.name}  coincide: {', '.join(matched)}"
                  f"  estado={fm.get('status', '?')}  verificada={fm.get('last_verified', '?')}")
            hits += 1
    if not hits:
        print("Sin coincidencias. No hay investigación previa registrada sobre estos términos.")
    return 0 if hits else 1


def cmd_show(root: Path, a) -> int:
    p = root / "docs" / "investigaciones" / f"{a.slug.removesuffix('.md')}.md"
    if not p.exists():
        print(f"No existe {p.relative_to(root)}")
        return 1
    fm, text, err = load(p)
    print(f"# {p.relative_to(root)}")
    for k, v in fm.items():
        print(f"{k}: {v}")
    if err:
        print(f"! frontmatter: {err}")
    print("\n## Encabezados (línea: título)")
    in_code = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and re.match(r"^#{1,3} ", line):
            print(f"{i}: {line}")
    return 0


def cmd_stale(root: Path, a) -> int:
    today = dt.date.today()
    found = 0
    for p in docs(root):
        fm, _, _ = load(p)
        reasons = []
        lv = str(fm.get("last_verified", ""))
        if DATE_RE.match(lv):
            age = (today - dt.date.fromisoformat(lv)).days
            if age > a.days:
                reasons.append(f"verificada hace {age} días")
        else:
            reasons.append(f"last_verified inválido: {lv!r}")
        if fm.get("status") in {"requiere-actualizacion", "obsoleta", "parcialmente-verificada", "borrador"}:
            reasons.append(f"estado={fm.get('status')}")
        if reasons:
            print(f"{p.stem}: {'; '.join(reasons)}")
            found += 1
    if not found:
        print(f"Ninguna investigación supera {a.days} días ni tiene estado dudoso.")
    return 1 if found else 0


def cmd_check(root: Path, _a) -> int:
    problems: list[str] = []
    base = root / "docs" / "investigaciones"
    idx = base / "INDEX.md"
    idx_text = idx.read_text(encoding="utf-8") if idx.exists() else ""
    if not idx.exists():
        problems.append("Falta docs/investigaciones/INDEX.md")
    today = dt.date.today()
    for p in docs(root):
        rel = p.relative_to(root)
        fm, text, err = load(p)
        if err:
            problems.append(f"{rel}: frontmatter: {err}")
        for f in REQUIRED_FIELDS:
            if f not in fm:
                problems.append(f"{rel}: falta campo '{f}'")
        for f in ("created", "updated", "last_verified"):
            v = str(fm.get(f, ""))
            if f in fm and not DATE_RE.match(v):
                problems.append(f"{rel}: '{f}' no es AAAA-MM-DD ({v!r})")
            elif DATE_RE.match(v) and dt.date.fromisoformat(v) > today:
                problems.append(f"{rel}: '{f}' es una fecha futura ({v})")
        if fm.get("status") and fm["status"] not in VALID_STATUS:
            problems.append(f"{rel}: status inválido {fm['status']!r}")
        if "source_count" in fm and not str(fm["source_count"]).isdigit():
            problems.append(f"{rel}: source_count no numérico")
        heads = {m.group(1).strip() for m in re.finditer(r"^## (.+)$", text, re.M)}
        for s in REQUIRED_SECTIONS:
            if s not in heads:
                problems.append(f"{rel}: falta sección '## {s}'")
        cited = set(re.findall(r"\[(S\d+|I\d+)\]", text))
        listed = set(re.findall(r"^\|\s*(S\d+|I\d+)\s*\|", text, re.M))
        for c in sorted(cited - listed):
            problems.append(f"{rel}: cita [{c}] sin entrada en Fuentes")
        if str(fm.get("source_count", "")).isdigit() and int(fm["source_count"]) != len(listed):
            problems.append(f"{rel}: source_count={fm['source_count']} pero hay {len(listed)} fuentes listadas")
        n = len(re.findall(rf"\]\({re.escape(p.name)}\)", idx_text))
        if n == 0:
            problems.append(f"{rel}: no aparece en INDEX.md")
        elif n > 1:
            problems.append(f"{rel}: aparece {n} veces en INDEX.md (duplicado)")
        for target in re.findall(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)", text):
            if not target.startswith("http") and not (p.parent / target).resolve().exists():
                problems.append(f"{rel}: enlace roto -> {target}")
    for target in re.findall(r"\]\(([^)#\s]+\.md)\)", idx_text):
        if not target.startswith("http") and not (base / target).exists():
            problems.append(f"INDEX.md: enlace roto -> {target}")
    for pr in problems:
        print(f"✗ {pr}")
    if not problems:
        print(f"✓ {len(docs(root))} investigaciones válidas; índice coherente.")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("search"); s.add_argument("terms", nargs="+")
    s = sub.add_parser("show"); s.add_argument("slug")
    s = sub.add_parser("stale"); s.add_argument("--days", type=int, default=180)
    sub.add_parser("check")
    a = ap.parse_args()
    root = find_root(a.root)
    return {"list": cmd_list, "search": cmd_search, "show": cmd_show,
            "stale": cmd_stale, "check": cmd_check}[a.cmd](root, a)


if __name__ == "__main__":
    sys.exit(main())
