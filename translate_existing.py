"""
One-time script: translate existing DB records that have empty _en fields.
Run once: venv/bin/python3 translate_existing.py
"""
import sqlite3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from translate import auto_fill_en

DB = os.path.join(os.path.dirname(__file__), 'data', 'wrestling.db')


def fill_table(conn, table, fields, pk='id'):
    """
    fields: list of base field names that have corresponding _en columns.
    e.g. ['title', 'location'] → reads title/title_en, writes to title_en.
    """
    cur = conn.execute(f"SELECT * FROM {table}")
    col_names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    # Only process fields that actually have a _en column
    valid = [f for f in fields if f + '_en' in col_names]
    if not valid:
        return 0

    updated = 0
    for row in rows:
        uk = {f: row[f] or '' for f in valid}
        en_cur = {f: row[f + '_en'] or '' for f in valid}

        if all(en_cur[f] for f in valid):
            continue  # already fully translated

        en_new = auto_fill_en(uk, en_cur)

        changed = {f + '_en': en_new[f] for f in valid if en_new.get(f) and not en_cur.get(f)}
        if not changed:
            continue

        sets = ', '.join(f"{col}=?" for col in changed)
        conn.execute(f"UPDATE {table} SET {sets} WHERE {pk}=?", list(changed.values()) + [row[pk]])
        updated += 1
        print(f"  [{table}#{row[pk]}] {(row[fields[0]] or '')[:50]!r}")

    return updated


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

tasks = [
    ('events',     ['title', 'location', 'category', 'description']),
    ('athletes',   ['name', 'weight_class', 'region', 'achievements']),
    ('leadership', ['name', 'role', 'bio']),
    ('secretariat',['name', 'role']),
    ('committees', ['name', 'description']),
    ('regions',    ['name', 'city', 'president']),
    ('champions',  ['name', 'competition']),
    ('news',       ['title']),
]

for table, fields in tasks:
    print(f"=== {table} ===")
    n = fill_table(conn, table, fields)
    print(f"  → {n} rows updated\n")

conn.commit()
conn.close()
print("Done.")
