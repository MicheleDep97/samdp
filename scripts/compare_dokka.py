import json, sys, subprocess, re
from pathlib import Path
from bs4 import BeautifulSoup

# Percorsi
HTML_ROOT = Path("app/build/dokka/html")
PAGES_JSON = HTML_ROOT / "scripts" / "pages.json"
SNAPSHOT   = Path("docs/json/old.json")
LOG        = Path("function_change_log.md")

# ---- util ----
def kebab_to_camel(s: str) -> str:
    parts = [p for p in s.split('-') if p]
    return parts[0] + ''.join(p.capitalize() for p in parts[1:]) if parts else s

def normalize_sig(sig: str) -> str:
    sig = sig.strip()
    sig = re.sub(r"\s+", " ", sig)
    sig = re.split(r"[\n\r{=]", sig, maxsplit=1)[0].strip()
    return sig

# Supporta sia fun normali che extension functions (fun Receiver.name(...))
NAME_RE = re.compile(r"\bfun\s+(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*\(")

def extract_name_from_sig(sig: str) -> str | None:
    m = NAME_RE.search(sig)
    return m.group(1) if m else None

# ---- parsing singola pagina ----
def load_functions_from_html(html_file: Path) -> dict[str, str]:
    try:
        soup = BeautifulSoup(html_file.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    except Exception:
        return {}

    candidates: list[str] = []

    # 1) <code>
    for code in soup.find_all("code"):
        txt = code.get_text(" ", strip=True)
        if "fun " in txt and "(" in txt:
            candidates.append(txt)

    # 2) <pre>
    if not candidates:
        for pre in soup.find_all("pre"):
            txt = pre.get_text(" ", strip=True)
            if "fun " in txt and "(" in txt:
                candidates.append(txt)

    # 3) Dokka temi recenti: <div class="symbol">, <div class="signature">, <span class="signature">
    if not candidates:
        for el in soup.select("div.symbol, div.signature, span.signature"):
            txt = el.get_text(" ", strip=True)
            if "fun " in txt and "(" in txt:
                candidates.append(txt)

    # 4) fallback grezzo: ultima spiaggia, cerca "fun xxx(" in tutto il body
    if not candidates:
        body_txt = soup.get_text(" ", strip=True)
        for m in re.finditer(r"\bfun\s+[A-Za-z_][A-Za-z0-9_.]*\s*\(", body_txt):
            # prendi una finestra di testo attorno alla firma per normalizzarla un minimo
            start = max(0, m.start() - 40)
            end   = min(len(body_txt), m.end() + 80)
            candidates.append(body_txt[start:end])

    results: dict[str, str] = {}
    for raw in candidates:
        sig  = normalize_sig(raw)
        name = extract_name_from_sig(sig)
        if not name:
            continue
        if name not in results or len(sig) > len(results[name]):
            results[name] = sig

    # 5) se ancora niente, deduci dal filename (kebab -> camel)
    if not results:
        stem = html_file.stem
        if stem not in {"index"} and not stem.startswith("-"):
            name = kebab_to_camel(stem)
            results[name] = f"fun {name}(…)"
    return results

# ---- scansione sito ----
def gather_functions_from_site() -> dict[str, str]:
    html_files: list[Path] = []

    if PAGES_JSON.exists():
        try:
            pages = json.loads(PAGES_JSON.read_text(encoding="utf-8"))
            for p in pages:
                loc = p.get("location") or ""
                if loc.endswith(".html"):
                    html_files.append(HTML_ROOT / loc)
        except Exception:
            pass

    if not html_files:
        # fallback: cerca direttamente sotto html/app/
        base = HTML_ROOT / "app"
        html_files = list(base.rglob("*.html")) if base.exists() else list(HTML_ROOT.rglob("*.html"))

    # log di cosa stiamo analizzando
    print(f"  HTML files to scan: {len(html_files)} (showing up to 20)")
    for f in html_files[:20]:
        print(f"   - {f.relative_to(HTML_ROOT)}")

    funcs: dict[str, str] = {}
    for f in html_files:
        if not f.exists():
            continue
        if f.name == "index.html" or f.name.startswith("-"):
            continue

        extracted = load_functions_from_html(f)

        if extracted:
            print(f"   ✓ {f.name}: found {len(extracted)} function(s)")
        else:
            # commenta se troppo rumoroso
            print(f"   • {f.name}: 0 functions")

        for name, sig in extracted.items():
            if name not in funcs or len(sig) > len(funcs[name]):
                funcs[name] = sig
    return funcs

# ---- snapshot io ----
def read_snapshot() -> dict[str, str]:
    if not SNAPSHOT.exists():
        return {}
    try:
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "functions" in data and isinstance(data["functions"], dict):
            return {str(k): str(v) for k, v in data["functions"].items()}
        if isinstance(data, list):
            return {str(k): "" for k in data}
        return {}
    except Exception:
        return {}

def write_snapshot(funcs: dict[str, str]):
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({"functions": dict(sorted(funcs.items()))}, ensure_ascii=False, indent=2),
                        encoding="utf-8")

def write_log(rows: list[tuple[str, str]], sha: str, date: str):
    with open(LOG, "w", encoding="utf-8") as out:
        out.write("| Function | Status   | Commit SHA | Date |\n")
        out.write("|----------|----------|------------|------|\n")
        if not rows:
            out.write(f"| _No changes_ | - | {sha} | {date} |\n")
        else:
            for f, s in rows:
                out.write(f"| {f} | {s} | {sha} | {date} |\n")

# ── main ───────────────────────────────────────────────────────────────
commit_sha  = subprocess.getoutput("git rev-parse HEAD").strip()
commit_date = subprocess.getoutput("git show -s --format=%ci HEAD").strip()

if not HTML_ROOT.exists():
    print(f" {HTML_ROOT} not found. Did you run dokkaHtml?")
    sys.exit(1)

new_funcs = gather_functions_from_site()
print(f"🔎 Parsed {len(new_funcs)} functions from Dokka HTML")

if not new_funcs:
    print(" No functions parsed from Dokka HTML (maybe all are private/internal?)")
    sys.exit(1)

old_funcs = read_snapshot()
print(f"📦 Snapshot contained {len(old_funcs)} functions")

if not old_funcs:
    write_snapshot(new_funcs)
    write_log([("_Initialized_", "-")], commit_sha, commit_date)
    print(" Snapshot initialized from Dokka HTML")
    sys.exit(0)

added   = sorted(set(new_funcs) - set(old_funcs))
removed = sorted(set(old_funcs) - set(new_funcs))
updated = sorted([f for f in set(new_funcs) & set(old_funcs) if new_funcs[f] != old_funcs[f]])

rows: list[tuple[str, str]] = []
rows += [(f, "new") for f in added]
rows += [(f, "deleted") for f in removed]
rows += [(f, "updated") for f in updated]

write_log(rows, commit_sha, commit_date)
write_snapshot(new_funcs)

print(" API comparison complete (HTML signatures). See function_change_log.md")
