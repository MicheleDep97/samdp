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
PATTERNS = {
    "function": re.compile(r"\bfun\s+(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*\("),
    "class": re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "interface": re.compile(r"\binterface\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "object": re.compile(r"\bobject\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "enum": re.compile(r"\benum\s+class\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "property": re.compile(r"\b(val|var)\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "typealias": re.compile(r"\btypealias\s+([A-Za-z_][A-Za-z0-9_]*)"),
}

def extract_symbol_from_sig(sig: str) -> tuple[str, str] | None:
    for kind, pat in PATTERNS.items():
        m = pat.search(sig)
        if m:
            if kind == "property":
                return m.group(2), kind
            return m.group(1), kind
    return None

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
        if any(x in txt for x in ("fun ", "class ", "interface ", "enum class ", "val ", "var ")):
            candidates.append(txt)

    # 2) <pre>
    if not candidates:
        for pre in soup.find_all("pre"):
            txt = pre.get_text(" ", strip=True)
            if any(x in txt for x in ("fun ", "class ", "interface ", "enum class ", "val ", "var ")):
                candidates.append(txt)

    # 3) Dokka temi recenti: <div class="symbol">, <div class="signature">, <span class="signature">
    if not candidates:
        for el in soup.select("div.symbol, div.signature, span.signature"):
            txt = el.get_text(" ", strip=True)
            if any(x in txt for x in ("fun ", "class ", "interface ", "enum class ", "val ", "var ")):
                candidates.append(txt)

    # 4) fallback grezzo: ultima spiaggia
    if not candidates:
        body_txt = soup.get_text(" ", strip=True)
        for m in re.finditer(r"\b(fun|class|interface|enum class|val|var)\s+[A-Za-z_][A-Za-z0-9_]*", body_txt):
            start = max(0, m.start() - 40)
            end   = min(len(body_txt), m.end() + 80)
            candidates.append(body_txt[start:end])

    results: dict[str, str] = {}
    for raw in candidates:
        sig = normalize_sig(raw)

        # Detect kind
        if sig.startswith("class "):
            name = sig.split()[1]
            kind = "class"
        elif sig.startswith("interface "):
            name = sig.split()[1]
            kind = "interface"
        elif sig.startswith("enum class "):
            name = sig.split()[2]
            kind = "enum"
        elif sig.startswith("val ") or sig.startswith("var "):
            name = sig.split()[1].split(":")[0]
            kind = "property"
        elif sig.startswith("fun "):
            name = sig.split()[1].split("(")[0]
            kind = "function"
        else:
            continue  # scarta roba che non riconosciamo

        key = f"{kind}:{name}"
        if key not in results or len(sig) > len(results[key]):
            results[key] = sig

    # fallback: dal filename se non abbiamo trovato niente
    if not results:
        stem = html_file.stem.lstrip('-')
        if stem != "index":
            name = kebab_to_camel(stem)
            results[f"function:{name}"] = f"fun {name}(…)"  # fallback

    return results


# ---- scansione sito ----
def gather_symbols_from_site() -> dict[str, str]:
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

    symbols: dict[str, str] = {}
    for f in html_files:
        if not f.exists():
            continue
        if f.name == "index.html":
            continue

        extracted = load_functions_from_html(f)

        if extracted:
            print(f"   ✓ {f.name}: found {len(extracted)} symbol(s)")
        else:
            print(f"   • {f.name}: 0 symbols")

        for name, sig in extracted.items():
            if name not in symbols or len(sig) > len(symbols[name]):
                symbols[name] = sig
    return symbols
    
# ---- snapshot io ----
def read_snapshot() -> dict[str, str]:
    """
    Ritorna il contenuto dello snapshot precedente come dict { "kind:name": "signature" }
    """
    if not SNAPSHOT.exists():
        return {}
    try:
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "symbols" in data and isinstance(data["symbols"], dict):
            return {str(k): str(v) for k, v in data["symbols"].items()}
        return {}
    except Exception:
        return {}

def write_snapshot(symbols: dict[str, str]):
    """
    Scrive il nuovo snapshot nel file old.json
    """
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(
        json.dumps({"symbols": dict(sorted(symbols.items()))}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def write_log(rows: list[tuple[str, str]], sha: str, date: str):
    """
    Scrive il log in formato tabella markdown
    """
    with open(LOG, "w", encoding="utf-8") as out:
        out.write("| Symbol | Kind | Status   | Commit SHA | Date |\n")
        out.write("|--------|------|----------|------------|------|\n")
        if not rows:
            out.write(f"| _No changes_ | - | - | {sha} | {date} |\n")
        else:
            for key, status in rows:
                if ":" in key:
                    kind, name = key.split(":", 1)  # es. "function:Hello"
                    out.write(f"| {name} | {kind} | {status} | {sha} | {date} |\n")
                else:
                    # caso speciale: inizializzazione o placeholder
                    out.write(f"| {key} | - | {status} | {sha} | {date} |\n")

# ── main ───────────────────────────────────────────────────────────────
commit_sha  = subprocess.getoutput("git rev-parse HEAD").strip()
commit_date = subprocess.getoutput("git show -s --format=%ci HEAD").strip()

if not HTML_ROOT.exists():
    print(f" {HTML_ROOT} not found. Did you run dokkaHtml?")
    sys.exit(1)

# Qui gather_symbols_from_site deve restituire { "kind:name": "signature" }
# Es: { "function:Hello": "fun Hello(name: String)", "class:MainActivity": "class MainActivity : ComponentActivity" }

new_symbols = gather_symbols_from_site()
print(f"🔎 Parsed {len(new_symbols)} symbols from Dokka HTML")

if not new_symbols:
    print("No symbols parsed from Dokka HTML (maybe all are private/internal?)")
    sys.exit(1)

old_symbols = read_snapshot()
print(f"📦 Snapshot contained {len(old_symbols)} symbols")

# Prima run → inizializza snapshot e log
if not old_symbols:
    write_snapshot(new_symbols)
    write_log([("_Initialized_", "-")], commit_sha, commit_date)
    print("Snapshot initialized from Dokka HTML")
    sys.exit(0)

# Diff tra vecchio e nuovo
added   = sorted(set(new_symbols) - set(old_symbols))
removed = sorted(set(old_symbols) - set(new_symbols))
updated = sorted([s for s in set(new_symbols) & set(old_symbols) if new_symbols[s] != old_symbols[s]])

rows: list[tuple[str, str]] = []
rows += [(s, "new") for s in added]
rows += [(s, "deleted") for s in removed]
rows += [(s, "updated") for s in updated]

write_log(rows, commit_sha, commit_date)
write_snapshot(new_symbols)

print("API comparison complete (HTML symbols). See function_change_log.md")
