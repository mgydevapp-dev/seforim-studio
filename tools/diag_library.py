"""Diagnose the pre-built library: which seforim have no text, and why."""
import json, sqlite3, sys, urllib.request, collections
lib = sqlite3.connect(sys.argv[1]); cat = sqlite3.connect("data/seforim_catalog.db")
q = lambda c, s, a=(): c.execute(s, a).fetchall()
print("== per top category: works / zero-passage works / passages")
for r in q(lib, "select top_category, count(*), sum(n_passages=0), sum(n_passages) from works group by 1 order by 2 desc"):
    print(r)
cat_ids = {r[0]: (r[1], r[2]) for r in q(cat, "select id,title,category_path from works")}
lib_ids = {r[0] for r in q(lib, "select id from works")}
missing = [cat_ids[i] for i in cat_ids if i not in lib_ids]
print("== in catalog but not in library:", len(missing))
for m in missing[:200]: print("  MISSING", m)
zero = q(lib, "select id,title,category_path from works where n_passages=0 order by category_path")
print("== zero passages:", len(zero))
for z in zero[:400]: print("  ZERO", z)
print("== Talmud works")
for r in q(lib, "select title, category_path, n_passages, (select count(*) from passages p where p.work_id=w.id and p.en!='') from works w where category_path like 'Talmud%' order by category_path, title"):
    print("  ", r)
print("== Berakhot sample refs:", q(lib, "select ref, substr(he,1,40), substr(en,1,40) from passages where work_id=487 order by seq limit 5"))
samples = [z[0] for z in zero[:6]] + [487]
for wid in samples:
    for lang, url in q(cat, "select language, json_url from books where work_id=? and is_merged=1", (wid,)):
        try:
            js = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SeforimStudio/1.0"}), timeout=90).read())
            t = js.get("text")
            print(f"-- {cat_ids[wid][0]} [{lang}] keys={list(js)[:12]} sectionNames={js.get('sectionNames')} "
                  f"text={type(t).__name__} len={len(t) if hasattr(t,'__len__') else ''} schema_keys={list((js.get('schema') or {}))[:10]}")
            if isinstance(t, dict): print("   text keys:", list(t)[:15])
            print("   head:", json.dumps(t, ensure_ascii=False)[:400])
        except Exception as e:
            print(f"-- {cat_ids[wid][0]} [{lang}] ERROR {e}")
