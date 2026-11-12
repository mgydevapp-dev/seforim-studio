# Error sweep

**1 problems**

- **console** `gematria › [שתהיה 20040]` — SLOW 32938ms /api/gematria_passages

## Slowest calls
```
   4.00s  translate  {"q": "peace"}
   3.89s  cross_lingual  {"q": "peace"}
   3.77s  cross_lingual  {"q": "שלום"}
   1.88s  els  {"work_id": 5914, "word": "תורה", "id": 3709374, "min": 2, "max": 60}
   1.46s  word_cloud  {"q": "שבת"}
   1.26s  gematria_phrases  {"value": 376}
   1.02s  search_compare  {"q": "שבת"}
   0.86s  plugin_call  {"id": "word_study", "fn": "study", "args": {"word": "אור"}}
   0.61s  cooccurrence  {"q": "שבת", "a": "שבת", "b": "שמירה"}
   0.58s  histogram  {"q": "שבת"}
   0.33s  search  {"q": "שלום", "lang": "he"}
   0.32s  roshei  {"letters": "שמע", "mode": "sofei"}
   0.30s  roshei  {"letters": "אבג"}
   0.28s  search  {"q": "אור", "lang": "he", "sort": "book"}
   0.27s  search  {"q": "אהב*", "lang": "he"}
   0.24s  translate  {"q": "שלום"}
   0.09s  lib_works  {}
   0.08s  catalog_tree  {}
   0.07s  search  {"q": "peace", "lang": "en"}
   0.07s  search  {"q": "\"קריאת שמע\"", "lang": "he"}
   0.05s  work_stats  {"work_id": 5914, "q": "אור", "a": "אור", "b": "חשך"}
   0.05s  connections  {"ref": "Genesis 1:1"}
   0.04s  search  {"q": "light AND darkness", "lang": "en"}
   0.02s  translate  {"q": "בראשית ברא אלהים"}
   0.02s  plugin_call  {"id": "mitzvos", "fn": "list"}
   0.02s  library_health  {}
   0.02s  he_coverage  {}
   0.02s  gematria_words  {"value": 376}
   0.01s  lib_toc  {"work_id": 4353}
   0.01s  lib_chapter  {"work_id": 5914, "node": "", "chapter": "1"}
   0.01s  lib_chapter  {"work_id": 4353, "node": "", "chapter": "2a"}
   0.01s  dashboard  {}
   0.01s  connections  {"ref": "Berakhot 2a:1"}
   0.00s  tools  {}
   0.00s  timeline  {}
   0.00s  status  {}
   0.00s  search_history  {}
   0.00s  reading_log  {}
   0.00s  plugins  {}
   0.00s  plugin_call  {"id": "tehillim", "fn": "texts", "args": {"refs": ["Psalms 119:1-8", "Psalms 20"]}}
```