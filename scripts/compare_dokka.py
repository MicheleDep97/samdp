import json, sys, subprocess, re
from pathlib import Path
from bs4 import BeautifulSoup

# Paths
HTML_ROOT = Path("app/build/dokka/html")
PAGES_JSON = HTML_ROOT / "scripts" / "pages.json"
SNAPSHOT = Path("docs/json/old.json")
LOG = Path("function_change_log.md")

# Helpers
def kebab_to_pascal(s: str) -> str:
    return ''.join(p.capitalize() for p in s.split('-') if p)

def normalize_sig(sig: str) -> str:
    sig = sig.strip()
    sig = re.sub(r"\s+", " ", sig)
    return re.split(r"[\n\r{=]", sig, maxsplit=1)[0].strip()

def extract_symbol_from_sig(sig: str) -> tuple[str, str] | None:
    patterns = {
        "function": re.compile(r"\bfun\s+(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        "class": re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"),
        "interface": re.compile(r"\binterface\s+([A-Za-z_][A-Za-z0-9_]*)"),
        "object": re.compile(r"\bobject\s+([A-Za-z_][A-Za-z0-9_]*)"),
        "enum": re.compile(r"\benum\s+class\s+([A-Za-z_][A-Za-z0-9_]*)"),
        "property": re.compile(r"\b(val|var)\s+([A-Za-z_][A-Za-z0-9_]*)"),
        "typealias": re.compile(r"\btypealias\s+([A-Za-z_][A-Za-z0-9_]*)"),
    }
    for kind, pat in patterns.items():
        m = pat.search(sig)
        if m:
            return (m.group(2) if kind == "property" else m.group(1), kind)
    return None

def detect_page_kind(soup: BeautifulSoup) -> str | None:
    txt = " ".join(el.get_text(" ", strip=True) for el in soup.select("h1,h2,h3,h4")).lower()
    if "enum entries" in txt or "enum class" in txt:
        return "enum"
    if "interface" in txt:
        return "interface"
    if re.search(r"\bobject\b", txt):
        return "object"
    if re.search(r"\bconstructors\b", txt) or re.search(r"\bfunctions\b", txt) or re.search(r"\bproperties\b", txt):
        return "class"
    return None

def load_functions_from_html(html_file: Path) -> dict[str, str]:
    try:
        soup = BeautifulSoup(html_file.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    except Exception:
        return {}

    if html_file.name == "index.html" and html_file.parent.name.startswith("-"):
        name = kebab_to_pascal(html_file.parent.name.lstrip('-'))
        kind = detect_page_kind(soup) or "class"
        return {f"{kind}:{name}": f"{kind} {name}"}

    candidates = []
    for tag in ["code", "pre"]:
        for el in soup.find_all(tag):
            txt = el.get_text(" ", strip=True)
            if any(kw in txt for kw in ["fun ", "class ", "interface ", "object", "enum", "val ", "var "]):
                candidates.append(txt)

    for el in soup.select("div.symbol, div.signature, span.signature"):
        txt = el.get_text(" ", strip=True)
        if any(kw in txt for kw in ["fun ", "class ", "interface ", "object", "enum", "val ", "var "]):
            candidates.append(txt)

    if not candidates:
        body_txt = soup.get_text(" ", strip=True)
        for m in re.finditer(r"\b(fun|class|interface|enum class|object|val|var)\s+[A-Za-z_][A-Za-z0-9_]*", body_txt):
            start = max(0, m.start() - 40)
            end = min(len(body_txt), m.end() + 80)
            candidates.append(body_txt[start:end])

    results = {}
    for raw in candidates:
        sig = normalize_sig(raw)
        symbol = extract_symbol_from_sig(sig)
        if not symbol:
            continue
        name, kind = symbol
        key = f"{kind}:{name}"
        if key not in results or len(sig) > len(results[key]):
            results[key] = sig

    if not results and html_file.stem != "index":
        name = kebab_to_pascal(html_file.stem)
        results[f"unknown:{name}"] = name

    return results

def gather_symbols_from_site() -> dict[str, str]:
    html_files = []
    if PAGES_JSON.exists():
        try:
            pages = json.loads(PAGES_JSON.read_text(encoding="utf-8"))
            html_files = [HTML_ROOT / p.get("location") for p in pages if p.get("location", "").endswith(".html")]
        except Exception:
            pass

    if not html_files:
        html_files = list(HTML_ROOT.rglob("*.html"))

    symbols = {}
    for f in html_files:
        extracted = load_functions_from_html(f)
        for key, sig in extracted.items():
            kind, name = (key.split(":") + ["unknown"])[:2]
            real_kinds = ("class", "interface", "enum", "object", "function", "property", "typealias")
            if kind == "unknown":
                if any(f"{rk}:{name}" in symbols for rk in real_kinds):
                    continue
            else:
                symbols.pop(f"unknown:{name}", None)
            if key not in symbols or len(sig) > len(symbols.get(key, "")):
                symbols[key] = sig
    return symbols

def read_snapshot() -> dict[str, str]:
    if not SNAPSHOT.exists():
        return {}
    try:
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        return data.get("symbols", {})
    except Exception:
        return {}

def write_snapshot(symbols: dict[str, str]):
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(
        json.dumps({"symbols": dict(sorted(symbols.items()))}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def normalize_name(key: str) -> str:
    return key.split(":")[-1]

def write_log(rows: list[tuple[str, str]], sha: str, date: str, symbols: dict[str, str]):
    with open(LOG, "w", encoding="utf-8") as out:
        out.write("| Symbol | Kind | Status   | Commit SHA | Date | Signature |\n")
        out.write("|--------|------|----------|------------|------|-----------|\n")
        if not rows:
            out.write(f"| _No changes_ | - | - | {sha} | {date} | - |\n")
        else:
            for key, status in rows:
                kind, name = key.split(":", 1) if ":" in key else ("-", key)
                sig = symbols.get(key, "-")
                out.write(f"| {name} | {kind} | {status} | {sha} | {date} | `{sig}` |\n")

# Main logic
commit_sha = subprocess.getoutput("git rev-parse HEAD").strip()
commit_date = subprocess.getoutput("git show -s --format=%ci HEAD").strip()

if not HTML_ROOT.exists():
    print(f"❌ {HTML_ROOT} not found. Did you run dokkaHtml?")
    sys.exit(1)

new_symbols = gather_symbols_from_site()
if not new_symbols:
    print("No symbols parsed from Dokka HTML.")
    sys.exit(1)

old_symbols = read_snapshot()

if not old_symbols:
    write_snapshot(new_symbols)
    write_log([("_Initialized_", "-")], commit_sha, commit_date, new_symbols)
    print("Snapshot initialized from Dokka HTML.")
    sys.exit(0)

# Normalize by name for smarter comparison
old_by_name = {normalize_name(k): k for k in old_symbols}
new_by_name = {normalize_name(k): k for k in new_symbols}

added = []
removed = []
updated = []

for name, old_key in old_by_name.items():
    new_key = new_by_name.get(name)
    if not new_key:
        removed.append(old_key)
    else:
        if new_symbols[new_key] != old_symbols[old_key]:
            updated.append(new_key)

for name, new_key in new_by_name.items():
    if name not in old_by_name:
        added.append(new_key)

rows = [(k, "new") for k in added] + [(k, "deleted") for k in removed] + [(k, "updated") for k in updated]

write_log(rows, commit_sha, commit_date, new_symbols)
write_snapshot(new_symbols)

print("API comparison complete. Changes written to function_change_log.md")
