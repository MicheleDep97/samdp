import sys
import csv
from bs4 import BeautifulSoup
from pathlib import Path

nav_html = Path(sys.argv[1])
commit_sha = sys.argv[2][:7]
date_str = sys.argv[3]
output_dir = Path(sys.argv[4])

master_csv = output_dir / "dev_function_history.csv"
snapshot_csv = output_dir / f"dev_function_history_{date_str}_{commit_sha}.csv"

# Parse Dokka HTML
with open(nav_html, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

functions = set()
for li in soup.select("nav li a"):
    text = li.get_text().strip()
    if text.startswith("fun "):
        name = text.split("fun ")[-1].split("(")[0].strip()
        functions.add(name)

# Load existing master CSV
existing = set()
rows = []
if master_csv.exists():
    with open(master_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 1:
                existing.add(row[0])
                rows.append(row)

# Write snapshot file
with open(snapshot_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    for func in sorted(functions):
        writer.writerow([func, commit_sha, date_str])

# Update master only with new functions
new_entries = []
for func in sorted(functions):
    if func not in existing:
        new_entries.append([func, commit_sha, date_str])
        rows.append([func, commit_sha, date_str])

# Save updated master CSV
if new_entries:
    with open(master_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

print(f"✅ Added {len(new_entries)} new function(s) to dev_function_history.csv")
