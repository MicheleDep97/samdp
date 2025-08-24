import json
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Percorsi
new_file = Path("app/build/dokka/json/module.json")
old_file = Path("docs/json/old.json")
log_file = Path("function_change_log.md")

def load_api(path: Path):
    with open(path) as f:
        data = json.load(f)
    return {
        n.get("name"): n
        for n in data.get("nodes", [])
        if n.get("kind") == "function"
    }

commit_sha = subprocess.getoutput("git rev-parse HEAD").strip()
commit_date = subprocess.getoutput("git show -s --format=%ci HEAD").strip()

# Verifica se esiste il JSON nuovo
if not new_file.exists():
    print(f"⚠️ No Dokka JSON file found at {new_file}")
    sys.exit(0)  # non blocca la pipeline

# Se non esiste il vecchio snapshot → inizializza
if not old_file.exists():
    print("ℹ️ No previous API snapshot. Saving current one for next run.")
    old_file.parent.mkdir(parents=True, exist_ok=True)
    old_file.write_text(new_file.read_text())
    sys.exit(0)

# Carichiamo API vecchio e nuovo
old_api = load_api(old_file)
new_api = load_api(new_file)

added = set(new_api) - set(old_api)
removed = set(old_api) - set(new_api)
common = set(old_api) & set(new_api)

changes = []
for f in added:
    changes.append((f, "new"))
for f in removed:
    changes.append((f, "deleted"))
for f in common:
    if old_api[f] != new_api[f]:
        changes.append((f, "updated"))

with open(log_file, "w") as out:
    out.write("| Function | Status   | Commit SHA | Date |\n")
    out.write("|----------|----------|------------|------|\n")
    if not changes:
        out.write(f"| _No changes_ | - | {commit_sha} | {commit_date} |\n")
    else:
        for f, status in changes:
            out.write(f"| {f} | {status} | {commit_sha} | {commit_date} |\n")

# Aggiorniamo snapshot
old_file.write_text(new_file.read_text())

print("✅ API comparison complete. See function_change_log.md")
