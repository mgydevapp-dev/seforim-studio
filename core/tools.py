"""Registry of Hebrew tools.  Each tool: id, name, category, description, inputs, fn(args, ctx) -> result.
Result is a string, or {"table": rows, "headers": [...]} or {"html": ...}."""
import datetime as dt
import re
import unicodedata
import urllib.parse
from collections import Counter

from . import hebrew as H
from . import hcalendar as C
from .data_tables import ABBREV_CLEAN, PARSHIYOS, HOLIDAY_TEXTS, MEASURES, VOLUMES, TIME_MEASURES, PLACES, ERAS

TOOLS = []
T = "text"; N = "number"; D = "date"; S = "select"; B = "bool"


def tool(cat, name, desc, inputs=None):
    def deco(fn):
        TOOLS.append({"id": fn.__name__, "name": name, "category": cat, "desc": desc,
                      "inputs": inputs or [{"name": "text", "label": "Hebrew text", "type": T}], "fn": fn})
        return fn
    return deco


def _txt(a): return a.get("text", "") or ""
def _date(a, k="date"): return dt.date.fromisoformat(a.get(k) or dt.date.today().isoformat())
def table(headers, rows): return {"headers": headers, "table": rows}


# ======================================================================== GEMATRIA (each method + extras)
def _make_gem(mname, fn):
    def f(a, ctx=None, _fn=fn):
        t = _txt(a)
        words = H.plain_words(t)
        rows = [[w, _fn(w)] for w in words] if len(words) > 1 else []
        total = _fn(t)
        if rows:
            return table(["Word", "Value"], rows + [["TOTAL", total]])
        return f"{t} = {total}"
    f.__name__ = "gem_" + re.sub(r"\W+", "_", mname.split("(")[0].strip().lower())
    TOOLS.append({"id": f.__name__, "name": "Gematria: " + mname, "category": "Gematria",
                  "desc": f"Numerical value using {mname}, with a per-word breakdown.",
                  "inputs": [{"name": "text", "label": "Hebrew word(s)", "type": T}], "fn": f})


for _m, _f in H.GEMATRIA_METHODS.items():
    _make_gem(_m, _f)


@tool("Gematria", "All gematria methods at once", "Shows the value of the text in every method side by side.")
def gem_all(a, ctx=None):
    t = _txt(a)
    return table(["Method", "Value"], [[m, f(t)] for m, f in H.GEMATRIA_METHODS.items()])


@tool("Gematria", "Equal-value words inside a text", "Groups the words of your text that share the same standard value.")
def gem_equal_in_text(a, ctx=None):
    groups = {}
    for w in set(H.plain_words(_txt(a))):
        groups.setdefault(H.g_standard(w), []).append(w)
    return table(["Value", "Words"], [[v, "، ".join(sorted(ws))] for v, ws in sorted(groups.items()) if len(ws) > 1]) or "No equal values"


@tool("Gematria", "Gematria between two phrases", "Compares two phrases in every method and marks the equal ones.",
      [{"name": "a", "label": "Phrase A", "type": T}, {"name": "b", "label": "Phrase B", "type": T}])
def gem_compare(a, ctx=None):
    return table(["Method", "A", "B", "Equal"], [[m, f(a.get("a", "")), f(a.get("b", "")), "✔" if f(a.get("a", "")) == f(a.get("b", "")) else ""]
                                                for m, f in H.GEMATRIA_METHODS.items()])


@tool("Gematria", "Katan reduction steps", "Reduces the standard value digit by digit to a single digit.")
def gem_reduce(a, ctx=None):
    n = H.g_standard(_txt(a)); steps = [n]
    while n > 9:
        n = sum(int(d) for d in str(n)); steps.append(n)
    return " → ".join(map(str, steps))


@tool("Gematria", "Words in library with this value", "Lists words from your downloaded seforim that equal the value of your text (or a number).",
      [{"name": "text", "label": "Hebrew text or number", "type": T}, {"name": "method", "label": "Method", "type": S, "options": list(H.GEMATRIA_METHODS)}])
def gem_library(a, ctx=None):
    t = _txt(a).strip()
    m = a.get("method") or "Standard (Mispar Hechrachi)"
    v = int(t) if t.isdigit() else H.GEMATRIA_METHODS[m](t)
    if not ctx or not ctx.get("library"):
        return "Library not loaded"
    rows = ctx["library"].gematria_words(v, m, 300)
    return table([f"Words = {v}", "Times in library"], [[r["word"], r["freq"]] for r in rows]) if rows else f"No words with value {v}"


# ======================================================================== NUMBERS
@tool("Numbers", "Number → Hebrew letters", "5787 → ה׳תשפ״ז, 15 → ט״ו, 16 → ט״ז.", [{"name": "n", "label": "Number", "type": N}])
def num_to_heb(a, ctx=None): return H.int_to_hebrew(int(a.get("n") or 0))


@tool("Numbers", "Hebrew letters → number", "ה׳תשפ״ז → 5787.")
def heb_to_num(a, ctx=None): return str(H.hebrew_to_int(_txt(a)))


@tool("Numbers", "Number in Hebrew words (feminine / counting)", "5787 → חמשת אלפים שבע מאות שמונים ושבע.", [{"name": "n", "label": "Number", "type": N}])
def num_words_f(a, ctx=None): return H.number_to_words(int(a.get("n") or 0), True)


@tool("Numbers", "Number in Hebrew words (masculine)", "18 → שמונה עשר.", [{"name": "n", "label": "Number", "type": N}])
def num_words_m(a, ctx=None): return H.number_to_words(int(a.get("n") or 0), False)


ORDINALS_M = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שביעי", "שמיני", "תשיעי", "עשירי"]


@tool("Numbers", "Hebrew ordinal (first, second…)", "1 → ראשון / ראשונה, up to 10.", [{"name": "n", "label": "Number 1-10", "type": N}])
def ordinal(a, ctx=None):
    n = int(a.get("n") or 1)
    if not 1 <= n <= 10: return "1-10 only"
    m = ORDINALS_M[n - 1]
    return f"{m} / {m + 'ה' if not m.endswith('י') else m + 'ת'}"


@tool("Numbers", "Hebrew numbering list", "Makes a list א׳, ב׳, ג׳ … for n items (for simanim/seifim).", [{"name": "n", "label": "How many", "type": N}])
def numbering_list(a, ctx=None): return "\n".join(H.int_to_hebrew(i) for i in range(1, min(1000, int(a.get("n") or 10)) + 1))


@tool("Numbers", "Daf number → amud label", "Converts 'daf 5 amud 2' or index to 5b / ה׳ ע״ב.",
      [{"name": "daf", "label": "Daf", "type": N}, {"name": "amud", "label": "Amud (1 or 2)", "type": N}])
def daf_label(a, ctx=None):
    d, am = int(a.get("daf") or 2), int(a.get("amud") or 1)
    if am not in (1, 2) or d < 1:
        raise ToolInputError("Daf must be 2 or more and amud must be 1 or 2.")
    return f"{d}{'ab'[am - 1]} — דף {H.int_to_hebrew(d)} {'ע״א' if am == 1 else 'ע״ב'}"


# ======================================================================== CIPHERS
for _n, _f, _d in [("Atbash (את״בש)", H.atbash, "א↔ת, ב↔ש …"), ("Albam (אל״בם)", H.albam, "א↔ל, ב↔מ …"),
                   ("Avgad (אב״גד)", H.avgad, "Each letter → next letter."), ("Reverse Avgad", H.reverse_avgad, "Each letter → previous letter."),
                   ("Achbi (אכ״בי)", H.achbi, "Atbash inside each half of the alef-beis."), ("Ayak Bachar (אי״ק בכ״ר)", H.ayak_bachar, "Letters sharing the same units digit rotate."),
                   ("Spell letters out (Milui)", H.milui_spell, "א → אלף, ב → בית …")]:
    def _cf(a, ctx=None, f=_f): return f(_txt(a))
    _cf.__name__ = "cipher_" + re.sub(r"\W+", "_", _n.split("(")[0].strip().lower())
    TOOLS.append({"id": _cf.__name__, "name": _n, "category": "Ciphers & letter play", "desc": _d,
                  "inputs": [{"name": "text", "label": "Hebrew text", "type": T}], "fn": _cf})


@tool("Ciphers & letter play", "Letter names in English", "Spell each letter's name (Alef, Bet …).")
def letter_names(a, ctx=None): return " ".join(H.LETTER_NAMES_EN[H.normalize_finals(c)] for c in H.letters_only(_txt(a)))


@tool("Ciphers & letter play", "Reverse letters", "Writes the text backwards.")
def reverse_letters(a, ctx=None): return _txt(a)[::-1]


@tool("Ciphers & letter play", "Reverse word order", "Keeps words, reverses their order.")
def reverse_words(a, ctx=None): return " ".join(_txt(a).split()[::-1])


@tool("Ciphers & letter play", "Palindrome words in text", "Lists words that read the same backwards.")
def palindromes(a, ctx=None): return ", ".join(sorted({w for w in H.plain_words(_txt(a)) if H.is_palindrome(w)})) or "None"


@tool("Ciphers & letter play", "Missing letters of the Alef-Beis", "Which letters never appear in the text (pangram check).")
def missing_letters(a, ctx=None):
    used = set(H.normalize_finals(H.letters_only(_txt(a))))
    miss = [c for c in H.LETTERS if c not in used]
    return "Uses all 22 letters ✔" if not miss else "Missing: " + " ".join(miss)


@tool("Ciphers & letter play", "Acrostic (first letter of each line)", "Reads the first letters of each line — finds hidden names in poems.")
def acrostic(a, ctx=None): return "".join((H.plain_words(l) or [" "])[0][0] for l in _txt(a).splitlines() if H.plain_words(l))


@tool("Ciphers & letter play", "Telestich (last letter of each line)", "Reads the last letters of each line.")
def telestich(a, ctx=None): return "".join((H.plain_words(l) or [" "])[-1][-1] for l in _txt(a).splitlines() if H.plain_words(l))


@tool("Ciphers & letter play", "Name with pesukim letters", "Shows first & last letter of your name for choosing a 'pasuk for a name'.")
def name_pasuk(a, ctx=None):
    w = H.letters_only(_txt(a))
    return f"Start letter: {w[:1]}   End letter: {w[-1:]} — choose a pasuk beginning with {w[:1]} and ending with {w[-1:]}" if w else ""


# ======================================================================== TEXT CLEANUP
_clean = [
    ("Remove nikud and ta'amim", H.remove_nikud, "Strips vowels and cantillation, keeps letters."),
    ("Remove ta'amim only (keep nikud)", lambda s: H.RE_TAAMIM.sub("", s), "Strips cantillation but keeps vowels."),
    ("Letters only", lambda s: " ".join(H.plain_words(s)), "Keeps only Hebrew letters and single spaces."),
    ("Fix final letters (sofiyos)", H.fix_final_letters, "Puts ך ם ן ף ץ at word ends and regular forms inside words."),
    ("Normalize final letters to regular", H.normalize_finals, "ך→כ, ם→מ, ן→נ, ף→פ, ץ→צ."),
    ("ASCII quotes → gershayim", H.to_gershayim, "רש\"י → רש״י, ר' → ר׳."),
    ("Gershayim → ASCII quotes", H.from_gershayim, "רש״י → רש\"י."),
    ("Maqaf → space", lambda s: s.replace("־", " "), "Replaces ־ with a space."),
    ("Remove (parentheses) content", lambda s: re.sub(r"\s*\([^)]*\)", "", s), "Deletes everything in round brackets."),
    ("Remove [brackets] content", lambda s: re.sub(r"\s*\[[^\]]*\]", "", s), "Deletes editorial insertions in square brackets."),
    ("Remove HTML tags", H.strip_html, "Strips <b>, <i> and other markup."),
    ("Collapse whitespace", lambda s: re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", s)).strip(), "Removes double spaces and blank-line runs."),
    ("Remove punctuation", lambda s: re.sub(r"[^\w\s֑-ׇ׳״\"']", "", s), "Deletes . , : ; ! ? etc."),
    ("Split into sentences", lambda s: re.sub(r"([.:׃!?])\s*", r"\1\n", s).strip(), "One sentence per line (. : ׃ ! ?)."),
    ("Join lines into a paragraph", lambda s: " ".join(l.strip() for l in s.splitlines() if l.strip()), "Removes hard line breaks."),
    ("Remove verse/line numbers", lambda s: re.sub(r"(^|\s)[\(\[]?\d+[\)\]\.]?(?=\s)", r"\1", s), "Deletes 1, (2), 3. style numbers."),
    ("Add right-to-left marks", H.add_rlm, "Stops punctuation jumping to the wrong side when pasting into other apps."),
    ("Remove sof-pasuk, paseq, {פ}{ס}", lambda s: re.sub(r"\s*\{[פס]\}", "", s).replace("׃", "").replace("׀", ""), "Cleans Tanach markers."),
    ("Mark unreadable words [???]", lambda s: re.sub(r"\?{2,}|_{2,}", "[???]", s), "Turns ?? or __ into the [???] placeholder."),
]
for _n, _f, _d in _clean:
    def _cl(a, ctx=None, f=_f): return f(_txt(a))
    _cl.__name__ = "clean_" + re.sub(r"\W+", "_", _n.lower())[:40]
    TOOLS.append({"id": _cl.__name__, "name": _n, "category": "Text cleanup", "desc": _d,
                  "inputs": [{"name": "text", "label": "Text", "type": T}], "fn": _cl})


@tool("Text cleanup", "Clean Unicode (paste from Word/web)", "Removes hidden characters, zero-width marks, odd spaces, and normalizes letters (NFC).")
def clean_unicode(a, ctx=None):
    s = unicodedata.normalize("NFC", _txt(a))
    s = re.sub(r"[​-‍⁠﻿­‪-‮⁦-⁩]", "", s)
    s = s.replace(" ", " ").replace(" ", " ").replace("\r\n", "\n")
    s = s.replace("שׁ", "שׁ").replace("שׂ", "שׂ").replace("וֹ", "וֹ")
    return re.sub(r"[ \t]+", " ", s)


@tool("Text cleanup", "Auto-correct common Hebrew typos", "Fixes final-letter misuse, double spaces, latin lookalikes, wrong-keyboard words.")
def autocorrect(a, ctx=None):
    s = _txt(a)
    words = []
    for w in s.split(" "):
        if w and re.fullmatch(r"[a-z;,.']+", w) and len(w) > 2:
            cand = H.en_layout_to_he(w)
            if H.has_hebrew(cand):
                w = cand
        words.append(w)
    s = " ".join(words)
    s = H.fix_final_letters(s)
    return re.sub(r" {2,}", " ", s).replace(" ,", ",").replace(" .", ".")


@tool("Text cleanup", "Color-code brackets (HTML)", "Shows (parentheses) in blue and [insertions] in brown.")
def color_brackets(a, ctx=None):
    s = _txt(a).replace("&", "&amp;").replace("<", "&lt;")
    s = re.sub(r"\(([^)]*)\)", r"<span style='color:#2563eb'>(\1)</span>", s)
    s = re.sub(r"\[([^\]]*)\]", r"<span style='color:#a16207'>[\1]</span>", s)
    return {"html": f"<div dir='rtl' style='white-space:pre-wrap'>{s}</div>"}


# ======================================================================== KEYBOARD & TRANSLITERATION
@tool("Keyboard & transliteration", "Fix text typed with English keyboard", "akuo → שלום (you forgot to switch to Hebrew).")
def kb_en_to_he(a, ctx=None): return H.en_layout_to_he(_txt(a))


@tool("Keyboard & transliteration", "Fix text typed with Hebrew keyboard", "יקךךם → hello.")
def kb_he_to_en(a, ctx=None): return H.he_layout_to_en(_txt(a))


@tool("Keyboard & transliteration", "Transliterate (Ashkenazi)", "בְּרֵאשִׁית → bereishis. Works best with nikud.")
def translit_ash(a, ctx=None): return H.transliterate(_txt(a), True)


@tool("Keyboard & transliteration", "Transliterate (Sephardi / Modern)", "בְּרֵאשִׁית → bereshit.")
def translit_sef(a, ctx=None): return H.transliterate(_txt(a), False)


@tool("Keyboard & transliteration", "English name → Hebrew letters", "Moshe Cohen → מושה קוהן (phonetic, check spelling).",
      [{"name": "text", "label": "English", "type": T}])
def en_name_to_he(a, ctx=None): return H.english_to_hebrew_letters(_txt(a))


@tool("Keyboard & transliteration", "Keyboard layout chart", "Shows which English key types which Hebrew letter.", [])
def kb_chart(a, ctx=None):
    return table(["English key", "Hebrew"], [[k, v] for k, v in H.EN_TO_HE.items()])


NIKUD_KEYS = [("Kamatz", "ָ"), ("Patach", "ַ"), ("Tzere", "ֵ"), ("Segol", "ֶ"), ("Sheva", "ְ"),
              ("Chirik", "ִ"), ("Cholam", "ֹ"), ("Kubutz", "ֻ"), ("Dagesh / Shuruk", "ּ"),
              ("Chataf Patach", "ֲ"), ("Chataf Segol", "ֱ"), ("Chataf Kamatz", "ֳ"), ("Shin dot", "ׁ"),
              ("Sin dot", "ׂ"), ("Rafe", "ֿ"), ("Meteg", "ֽ"), ("Maqaf", "־"), ("Geresh", "׳"), ("Gershayim", "״")]


@tool("Keyboard & transliteration", "Nikud & ta'amim shortcut chart", "Keyboard shortcuts for vowels in the Notes editor (Alt+key).", [])
def nikud_chart(a, ctx=None):
    keys = "1234567890-=qwertyuio"
    return table(["Mark", "Shortcut", "Example"], [[n, "Alt+" + keys[i] if i < len(keys) else "", "ב" + m] for i, (n, m) in enumerate(NIKUD_KEYS)])


# ======================================================================== ANALYSIS
@tool("Text analysis", "Count words, letters, characters", "Word, letter, nikud and line counts.")
def counts(a, ctx=None):
    s = _txt(a)
    return table(["Measure", "Count"], [["Words", len(H.plain_words(s)) or len(s.split())], ["Hebrew letters", len(H.letters_only(s))],
                                        ["All characters", len(s)], ["Nikud/ta'amim marks", len(H.RE_ALL_MARKS.findall(s))],
                                        ["Lines", len(s.splitlines())], ["Unique words", len(set(H.plain_words(s)))]])


@tool("Text analysis", "Letter frequency", "How many times each letter appears.")
def letter_freq(a, ctx=None):
    c = H.letter_frequency(_txt(a)); tot = sum(c.values()) or 1
    return table(["Letter", "Count", "%"], [[l, c[l], round(100 * c[l] / tot, 1)] for l in H.LETTERS if c[l]])


@tool("Text analysis", "Word frequency", "Most common words in the text.")
def word_freq(a, ctx=None): return table(["Word", "Count"], Counter(H.plain_words(_txt(a))).most_common(100))


@tool("Text analysis", "Unique words (alphabetical)", "Distinct words sorted by alef-beis.")
def unique_words(a, ctx=None): return " ".join(sorted(set(H.plain_words(_txt(a))), key=lambda w: [H.ALL_LETTERS.find(c) for c in H.normalize_finals(w)]))


@tool("Text analysis", "Longest words", "The 20 longest words.")
def longest(a, ctx=None): return table(["Word", "Letters"], [[w, len(w)] for w in sorted(set(H.plain_words(_txt(a))), key=len, reverse=True)[:20]])


@tool("Text analysis", "Extract roshei teivos", "First letter of every word.")
def extract_rt(a, ctx=None): return H.roshei_teivos(_txt(a))


@tool("Text analysis", "Extract sofei teivos", "Last letter of every word.")
def extract_st(a, ctx=None): return H.sofei_teivos(_txt(a))


@tool("Text analysis", "Make an abbreviation", "רבי משה בן מימון → רמב״ם (adds gershayim before the last letter).")
def make_abbrev(a, ctx=None):
    r = H.fix_final_letters(H.roshei_teivos(_txt(a)))
    return r[:-1] + "״" + r[-1] if len(r) > 1 else r + "׳"


@tool("Text analysis", "Expand abbreviation (ראשי תיבות)", "רמב״ם → רבי משה בן מימון, from a built-in dictionary of common abbreviations.")
def expand_abbrev(a, ctx=None):
    k = H.normalize_finals(H.letters_only(_txt(a)))
    return ABBREV_CLEAN.get(k) or "Not in dictionary — try the Roshei Teivos tab to search the library."


@tool("Text analysis", "Expand all abbreviations in a text", "Replaces every known abbreviation (with ״ or \") by its full form.")
def expand_all(a, ctx=None):
    def rep(m):
        k = H.normalize_finals(H.letters_only(m.group(0)))
        return ABBREV_CLEAN.get(k, m.group(0))
    return re.sub(r"[א-ת]+[\"״'׳][א-ת]*", rep, _txt(a))


@tool("Text analysis", "Abbreviation dictionary search", "Finds abbreviations whose expansion contains your word.", [{"name": "text", "label": "Word (e.g. משה)", "type": T}])
def abbrev_search(a, ctx=None):
    w = _txt(a).strip()
    return table(["Abbreviation", "Meaning"], [[H.fix_final_letters(k), v] for k, v in ABBREV_CLEAN.items() if w and (w in v or w in k)][:200])


@tool("Text analysis", "Gematria of every line", "Standard value per line (useful for poems and piyutim).")
def gem_lines(a, ctx=None): return table(["Line", "Value"], [[l.strip()[:60], H.g_standard(l)] for l in _txt(a).splitlines() if l.strip()])


@tool("Text analysis", "Nikud coverage check", "Lists words that have no vowels (to find what still needs nikud).")
def nikud_check(a, ctx=None):
    bare = [m.group(0) for m in H.RE_WORD_UNIT.finditer(_txt(a)) if not H.RE_NIKUD.search(m.group(0))]
    return f"{len(bare)} words without nikud: " + " ".join(bare[:200]) if bare else "Every word has nikud ✔"


@tool("Text analysis", "Language mix", "Percentage of Hebrew vs English letters.")
def lang_mix(a, ctx=None):
    s = _txt(a); h, l = len(H.RE_HEB.findall(s)), len(H.RE_LAT.findall(s)); t = h + l or 1
    return f"Hebrew {round(100 * h / t)}%  •  English {round(100 * l / t)}%"


@tool("Text analysis", "Find placeholders [???]", "Lists every [???] or unreadable marker with its line number.")
def find_placeholders(a, ctx=None):
    return table(["Line", "Text"], [[i + 1, l.strip()[:80]] for i, l in enumerate(_txt(a).splitlines()) if "[???]" in l or "??" in l]) or "None found"


@tool("Text analysis", "Detect citations in text", "Finds references like Genesis 1:1, Berakhot 2a, בראשית א:ב and links them to your library.")
def detect_cites(a, ctx=None):
    if not ctx or not ctx.get("library"):
        return "Library not loaded"
    from .library import detect_citations
    lib = ctx["library"]
    titles = [w["title"] for w in lib.works()] + [w["he_title"] for w in lib.works() if w["he_title"]]
    from .order import HE_NAMES
    titles += list(HE_NAMES.values()) + list(HE_NAMES.keys())
    rows = []
    he2en = {v: k for k, v in HE_NAMES.items()}
    for c in detect_citations(_txt(a), list(set(titles))):
        ref = c["ref"]
        t = c["title"]
        if t in he2en:
            ref = he2en[t] + ref[len(t):]
        found = lib.find_ref(ref)
        rows.append([c["text"], ref, "✔ in library" if found else "not downloaded"])
    return table(["Found", "Reference", "Status"], rows) if rows else "No citations found"


@tool("Text analysis", "Sefaria link for a reference", "Makes a web link anyone can open (Genesis 1:1 → sefaria.org/Genesis.1.1).", [{"name": "text", "label": "Reference", "type": T}])
def sefaria_link(a, ctx=None):
    r = _txt(a).strip()
    m = re.match(r"^(.*?)\s+([\dab:\-]+)$", r)
    path = (m.group(1).replace(" ", "_") + "." + m.group(2).replace(":", ".")) if m else r.replace(" ", "_")
    return "https://www.sefaria.org/" + urllib.parse.quote(path, safe="._-")


# ======================================================================== CALENDAR
@tool("Calendar", "Today's Hebrew date", "Hebrew and English date for today, with holidays, omer and daf yomi.", [])
def today(a, ctx=None):
    d = dt.date.today(); y, m, dd = C.greg_to_heb(d)
    out = [["Hebrew date", C.format_hebrew(y, m, dd)], ["English", C.format_hebrew(y, m, dd, False)],
           ["Day", C.DAYS_EN[C.weekday_index(d)] + " / יום " + C.DAYS_HE[C.weekday_index(d)]],
           ["Parasha this week", C.parasha(d)], ["Daf Yomi", " — ".join(map(str, C.daf_yomi(d)[1:])) + f" ({C.daf_yomi(d)[0]})"]]
    for en, he in C.holiday_on(d):
        out.append(["Today", f"{en} — {he}"])
    if C.omer_day(d):
        out.append(["Omer", C.omer_text(C.omer_day(d))])
    return table(["", ""], out)


@tool("Calendar", "Gregorian → Hebrew date", "Converts any date. Tick 'after sunset' for the next Hebrew day.",
      [{"name": "date", "label": "Date", "type": D}, {"name": "after_sunset", "label": "After sunset", "type": B}])
def g2h(a, ctx=None):
    d = _date(a) + dt.timedelta(days=1 if a.get("after_sunset") else 0)
    y, m, dd = C.greg_to_heb(d)
    return f"{C.format_hebrew(y, m, dd)}  —  {C.format_hebrew(y, m, dd, False)}"


@tool("Calendar", "Hebrew → Gregorian date", "Enter Hebrew day, month and year (year can be 5787 or תשפ״ז).",
      [{"name": "day", "label": "Day (1-30 or א-ל)", "type": T}, {"name": "month", "label": "Month", "type": S,
        "options": ["Tishrei", "Cheshvan", "Kislev", "Tevet", "Shevat", "Adar / Adar I", "Adar II", "Nisan", "Iyar", "Sivan", "Tammuz", "Av", "Elul"]},
       {"name": "year", "label": "Year", "type": T}])
def h2g(a, ctx=None):
    mm = {"Tishrei": 7, "Cheshvan": 8, "Kislev": 9, "Tevet": 10, "Shevat": 11, "Adar / Adar I": 12, "Adar II": 13, "Nisan": 1,
          "Iyar": 2, "Sivan": 3, "Tammuz": 4, "Av": 5, "Elul": 6}.get(a.get("month") or "Tishrei") or int(a.get("month"))
    def num(v):
        v = str(v or "").strip()
        return int(v) if v.isdigit() else H.hebrew_to_int(v)
    d, y = num(a.get("day") or 1), num(a.get("year") or C.greg_to_heb(dt.date.today())[0])
    if y < 1000: y += 5000
    if mm == 13 and not C.is_leap(y): return f"{y} is not a leap year (no Adar II)"
    g = C.heb_to_greg(y, mm, d)
    return f"{g:%A, %B %d, %Y}"


@tool("Calendar", "Hebrew year information", "Leap year, length, type, Rosh Hashana day, 19-year cycle, shmita.", [{"name": "year", "label": "Hebrew year (e.g. 5787)", "type": N}])
def year_info(a, ctx=None):
    i = C.year_info(int(a.get("year") or C.greg_to_heb(dt.date.today())[0]))
    return table(["", ""], [[k.replace("_", " ").title(), str(v)] for k, v in i.items()])


@tool("Calendar", "Holidays & fasts for a year", "All yamim tovim, fasts and Rosh Chodesh with dates.",
      [{"name": "year", "label": "Hebrew year", "type": N}, {"name": "israel", "label": "Eretz Yisrael", "type": B}])
def holidays(a, ctx=None):
    y = int(a.get("year") or C.greg_to_heb(dt.date.today())[0])
    return table(["Date", "Day", "Holiday", "חג"], [[f"{g:%b %d %Y}", C.DAYS_EN[C.weekday_index(g)], en, he] for g, en, he in C.holidays(y, bool(a.get("israel")))])


@tool("Calendar", "Next holiday countdown", "How many days until the next yom tov / fast.", [])
def next_holiday(a, ctx=None):
    d = dt.date.today(); y = C.greg_to_heb(d)[0]
    for g, en, he in C.holidays(y) + C.holidays(y + 1):
        if g >= d and not en.startswith("Rosh Chodesh"):
            return f"{en} ({he}) — {g:%A %b %d %Y} — in {(g - d).days} days"


@tool("Calendar", "Parasha for a date", "Weekly Torah portion for the Shabbos of that week.",
      [{"name": "date", "label": "Date", "type": D}, {"name": "israel", "label": "Eretz Yisrael", "type": B}])
def parasha(a, ctx=None): return C.parasha(_date(a), bool(a.get("israel"))) + "  /  " + C.parasha(_date(a), bool(a.get("israel")), True)


@tool("Calendar", "Parasha → pesukim range", "Start and end verses of every parasha (opens in library).",
      [{"name": "text", "label": "Parasha (blank = all)", "type": T}])
def parasha_refs(a, ctx=None):
    t = _txt(a).strip().lower()
    return table(["Parasha", "פרשה", "From", "To"], [list(p) for p in PARSHIYOS if not t or t in p[0].lower() or t in p[1]])


@tool("Calendar", "Holiday → learning texts", "Readings and sugyos connected to each holiday.", [{"name": "text", "label": "Holiday (blank = all)", "type": T}])
def holiday_texts(a, ctx=None):
    t = _txt(a).strip().lower()
    return table(["Holiday", "Texts"], [[k, ", ".join(v)] for k, v in HOLIDAY_TEXTS.items() if not t or t in k.lower()])


@tool("Calendar", "Sefiras HaOmer for a date", "Omer count with the bracha text day and sefirah.", [{"name": "date", "label": "Date (evening counts next day)", "type": D}])
def omer(a, ctx=None):
    n = C.omer_day(_date(a)); return C.omer_text(n) if n else "Not during the Omer"


@tool("Calendar", "Molad of a month", "Time of the molad for any Hebrew month.",
      [{"name": "year", "label": "Hebrew year", "type": N}, {"name": "month", "label": "Month number (Nisan=1 … Tishrei=7 … Adar II=13)", "type": N}])
def molad(a, ctx=None):
    return C.molad_text(int(a.get("year") or C.greg_to_heb(dt.date.today())[0]), int(a.get("month") or C.greg_to_heb(dt.date.today())[1]))


@tool("Calendar", "Molad for the next 12 months", "Upcoming molados.", [])
def molad_list(a, ctx=None):
    y, m, _ = C.greg_to_heb(dt.date.today()); rows = []
    for _ in range(12):
        m = m + 1
        if m > C.last_month(y): m = 1
        if m == 7: y += 1
        rows.append([C.month_name(m, y), C.molad_text(y, m)])
    return table(["Month", "Molad"], rows)


@tool("Calendar", "Yahrzeit dates", "Upcoming yahrzeit dates from the date of passing.",
      [{"name": "date", "label": "Date of passing", "type": D}, {"name": "after_sunset", "label": "After sunset", "type": B}])
def yahrzeit(a, ctx=None):
    return table(["Date", "Hebrew date"], [[f"{g:%A %b %d %Y}", h] for g, h in C.yahrzeit(_date(a), bool(a.get("after_sunset")))])


@tool("Calendar", "Hebrew birthday dates", "Your Hebrew birthday for the next 10 years.",
      [{"name": "date", "label": "Birth date", "type": D}, {"name": "after_sunset", "label": "After sunset", "type": B}])
def hebrew_birthday(a, ctx=None):
    return table(["Date", "Hebrew date"], [[f"{g:%A %b %d %Y}", h] for g, h in C.hebrew_birthday(_date(a), bool(a.get("after_sunset")))])


@tool("Calendar", "Bar Mitzvah date", "13th Hebrew birthday.", [{"name": "date", "label": "Birth date", "type": D}, {"name": "after_sunset", "label": "After sunset", "type": B}])
def bar_mitzvah(a, ctx=None):
    g, h = C.bar_mitzvah(_date(a), bool(a.get("after_sunset"))); return f"{g:%A %B %d %Y} — {h}"


@tool("Calendar", "Bas Mitzvah date", "12th Hebrew birthday.", [{"name": "date", "label": "Birth date", "type": D}, {"name": "after_sunset", "label": "After sunset", "type": B}])
def bas_mitzvah(a, ctx=None):
    g, h = C.bar_mitzvah(_date(a), bool(a.get("after_sunset")), 12); return f"{g:%A %B %d %Y} — {h}"


@tool("Calendar", "Daf Yomi for a date", "Bavli daf for any day.", [{"name": "date", "label": "Date", "type": D}])
def daf_yomi(a, ctx=None):
    n, d, he = C.daf_yomi(_date(a)); return f"{n} {d} — {he}"


@tool("Calendar", "Daf Yomi — next 30 days", "Schedule list.", [])
def daf_list(a, ctx=None):
    d = dt.date.today()
    return table(["Date", "Daf", "דף"], [[f"{d + dt.timedelta(i):%a %b %d}", f"{C.daf_yomi(d + dt.timedelta(i))[0]} {C.daf_yomi(d + dt.timedelta(i))[1]}",
                                          C.daf_yomi(d + dt.timedelta(i))[2]] for i in range(30)])


@tool("Calendar", "When does a masechta start in Daf Yomi?", "Next start and finish date of a masechta.",
      [{"name": "text", "label": "Masechta (e.g. Shabbat)", "type": T}])
def daf_masechta(a, ctx=None):
    t = _txt(a).strip().lower()
    d = dt.date.today()
    for i in range(C.CYCLE_DAYS + 1):
        n, daf, _ = C.daf_yomi(d + dt.timedelta(i))
        if n.lower().startswith(t) and (daf == 2 or (n in ("Kinnim", "Tamid", "Middot") and daf == dict((x[0], x[1]) for x in C.SHAS)[n])):
            start = d + dt.timedelta(i)
            cnt = next(b - a2 + 1 for x, a2, b in C.SHAS if x == n)
            return f"{n}: starts {start:%A %b %d %Y}, siyum {start + dt.timedelta(cnt - 1):%A %b %d %Y} ({cnt} days)"
    return "Masechta not found"


@tool("Calendar", "Days between two dates", "Counts days (and weeks).", [{"name": "date", "label": "From", "type": D}, {"name": "date2", "label": "To", "type": D}])
def days_between(a, ctx=None):
    n = (_date(a, "date2") - _date(a)).days; return f"{n} days ({n // 7} weeks and {n % 7} days)"


@tool("Calendar", "Date after N days", "Gregorian + Hebrew date N days from a date.", [{"name": "date", "label": "Start", "type": D}, {"name": "n", "label": "Days", "type": N}])
def date_plus(a, ctx=None):
    d = _date(a) + dt.timedelta(days=int(a.get("n") or 0)); return f"{d:%A %b %d %Y} — {C.format_hebrew(*C.greg_to_heb(d))}"


@tool("Calendar", "Leap years in a range", "Which Hebrew years have Adar II.", [{"name": "year", "label": "From year", "type": N}, {"name": "n", "label": "How many years", "type": N}])
def leap_years(a, ctx=None):
    y = int(a.get("year") or C.greg_to_heb(dt.date.today())[0])
    return ", ".join(f"{x} ({H.int_to_hebrew(x)})" for x in range(y, y + int(a.get("n") or 19)) if C.is_leap(x))


@tool("Calendar", "Shmita years", "Upcoming shmita years.", [])
def shmita(a, ctx=None):
    y = C.greg_to_heb(dt.date.today())[0]
    return ", ".join(f"{x} ({H.int_to_hebrew(x)}) = {C.heb_to_greg(x, 7, 1).year}-{C.heb_to_greg(x, 7, 1).year + 1}" for x in range(y, y + 30) if x % 7 == 0)


@tool("Calendar", "Birkas HaChama", "The next blessing on the sun (every 28 years).", [])
def birkas_hachama(a, ctx=None):
    y = 2037
    while y < dt.date.today().year: y += 28
    return f"Next Birkas HaChama: Wednesday morning, April 8, {y} (previous: April 8, 2009)"


@tool("Calendar", "Rosh Chodesh list for a year", "Every Rosh Chodesh day.", [{"name": "year", "label": "Hebrew year", "type": N}])
def rosh_chodesh(a, ctx=None):
    y = int(a.get("year") or C.greg_to_heb(dt.date.today())[0])
    return table(["Date", "Rosh Chodesh"], [[f"{g:%a %b %d %Y}", en] for g, en, he in C.holidays(y) if en.startswith("Rosh Chodesh")])


@tool("Calendar", "Month calendar (Hebrew + English)", "A grid of the month with both dates.", [{"name": "date", "label": "Any day in the month", "type": D}])
def month_grid(a, ctx=None):
    d = _date(a).replace(day=1)
    start = d - dt.timedelta(days=C.weekday_index(d))
    rows, cur = [], start
    while True:
        week = []
        for _ in range(7):
            y, m, dd = C.greg_to_heb(cur)
            hol = C.holiday_on(cur)
            cell = f"{cur.day}<br><b>{H.int_to_hebrew(dd)}</b> {C.month_name(m, y, True) if dd == 1 or cur == start else ''}"
            if hol: cell += f"<br><small style='color:#b45309'>{hol[0][1]}</small>"
            week.append(cell if cur.month == d.month else f"<span style='opacity:.35'>{cell}</span>")
            cur += dt.timedelta(days=1)
        rows.append(week)
        if cur.month != d.month and cur > d:
            break
    head = "".join(f"<th>{x}</th>" for x in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Shabbos"])
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return {"html": f"<h3>{d:%B %Y}</h3><table class='grid'><tr>{head}</tr>{body}</table>"}


# ======================================================================== ZMANIM
LOC = [{"name": "lat", "label": "Latitude", "type": N, "default": 40.744}, {"name": "lon", "label": "Longitude", "type": N, "default": -73.482},
       {"name": "tz", "label": "UTC offset (hours)", "type": N, "default": -5}]


@tool("Zmanim", "Zmanim for a date", "Alos, netz, sof zman shema (MGA/GRA), chatzos, mincha, plag, shkia, tzeis.",
      [{"name": "date", "label": "Date", "type": D}] + LOC)
def zmanim(a, ctx=None):
    z = C.zmanim(_date(a), float(a.get("lat") or 40.744), float(a.get("lon") or -73.482), float(a.get("tz") or -5))
    return table(["Zman", "Time"], [[k, (f"{v:%I:%M %p}" if isinstance(v, dt.datetime) else (f"{int(v.total_seconds() // 60)} min" if isinstance(v, dt.timedelta) else str(v)))] for k, v in z.items()])


@tool("Zmanim", "Shabbos times for the coming weeks", "Candle lighting and motzei Shabbos for 8 weeks.",
      LOC + [{"name": "n", "label": "Minutes before shkia", "type": N, "default": 18}])
def shabbos_times(a, ctx=None):
    lat, lon, tz = float(a.get("lat") or 40.744), float(a.get("lon") or -73.482), float(a.get("tz") or -5)
    d = dt.date.today(); fri = d + dt.timedelta(days=(4 - d.weekday()) % 7); rows = []
    for i in range(8):
        f = fri + dt.timedelta(weeks=i); s = f + dt.timedelta(days=1)
        zf, zs = C.zmanim(f, lat, lon, tz, int(a.get("n") or 18)), C.zmanim(s, lat, lon, tz)
        rows.append([f"{f:%b %d}", C.parasha(s), f"{zf['Candle lighting']:%I:%M %p}", f"{zs['Tzeis HaKochavim (8.5°)']:%I:%M %p}",
                     f"{zs['Rabbeinu Tam (72 min)']:%I:%M %p}"])
    return table(["Friday", "Parasha", "Candles", "Shabbos ends", "R. Tam"], rows)


@tool("Zmanim", "Is it day or night now?", "Tells whether it is after shkia / tzeis at your location (for the Hebrew date).", LOC)
def day_or_night(a, ctx=None):
    now = dt.datetime.now(); z = C.zmanim(now.date(), float(a.get("lat") or 40.744), float(a.get("lon") or -73.482), float(a.get("tz") or -5))
    if now < z["Netz / Sunrise"]: return "Before sunrise"
    if now < z["Shkia / Sunset"]: return f"Daytime — shkia at {z['Shkia / Sunset']:%I:%M %p}"
    if now < z["Tzeis HaKochavim (8.5°)"]: return "Bein hashmashos (twilight)"
    return "Night — the Hebrew date has advanced"


# ======================================================================== MEASURES
@tool("Halachic measures", "Length: amos, tefachim, etc.", "Converts ancient length units to cm/inches by R' Chaim Naeh and Chazon Ish.",
      [{"name": "n", "label": "Amount", "type": N}, {"name": "unit", "label": "Unit", "type": S, "options": list(MEASURES)}])
def measure_len(a, ctx=None):
    n = float(a.get("n") or 1); u = a.get("unit") or "Amah (cubit)"
    return table(["Opinion", "cm", "inches", "meters"], [[o, round(n * v, 1), round(n * v / 2.54, 1), round(n * v / 100, 2)] for o, v in MEASURES[u].items()])


@tool("Halachic measures", "Volume: kezayis, kebeitzah, revi'is…", "Converts to ml / fl oz.",
      [{"name": "n", "label": "Amount", "type": N}, {"name": "unit", "label": "Unit", "type": S, "options": list(VOLUMES)}])
def measure_vol(a, ctx=None):
    n = float(a.get("n") or 1); u = a.get("unit") or "Kezayis (olive)"
    return table(["Opinion", "ml", "fl oz", "cups"], [[o, round(n * v), round(n * v / 29.57, 1), round(n * v / 236.6, 2)] for o, v in VOLUMES[u].items()])


@tool("Halachic measures", "Modern → amos", "How many amos / tefachim in a modern length.", [{"name": "n", "label": "Centimeters", "type": N}])
def to_amos(a, ctx=None):
    cm = float(a.get("n") or 100)
    return table(["Opinion", "Amos", "Tefachim"], [[o, round(cm / MEASURES["Amah (cubit)"][o], 2), round(cm / MEASURES["Tefach (handbreadth)"][o], 1)] for o in MEASURES["Amah (cubit)"]])


@tool("Halachic measures", "Techum Shabbos", "2,000 amos in meters / miles.", [])
def techum(a, ctx=None):
    return table(["Opinion", "Meters", "Miles"], [[o, round(2000 * v / 100), round(2000 * v / 160934, 2)] for o, v in MEASURES["Amah (cubit)"].items()])


@tool("Halachic measures", "Mikveh: 40 se'ah", "Minimum mikveh volume in liters / gallons.", [])
def mikveh(a, ctx=None):
    return table(["Opinion", "Liters", "US gallons"], [["R' Chaim Naeh", 331.8, 87.7], ["Chazon Ish", 573.0, 151.4]])


@tool("Halachic measures", "Time measures", "Kdei achilas pras, hiluch mil.", [])
def time_measures(a, ctx=None):
    return table(["Measure", "Opinion", "Minutes"], [[k, o, v] for k, d in TIME_MEASURES.items() for o, v in d.items()])


@tool("Halachic measures", "Shiur challah", "Flour amount for separating challah.", [])
def challah(a, ctx=None):
    return table(["", "Grams of flour (approx.)"], [["With a bracha (common practice)", "≈ 1,666 g (3.67 lb)"], ["Without a bracha", "≈ 1,230 g (2.7 lb)"]])


@tool("Halachic measures", "Ma'aser calculator", "10% / 20% of an income amount.", [{"name": "n", "label": "Amount", "type": N}])
def maaser(a, ctx=None):
    n = float(a.get("n") or 0); return f"Ma'aser (10%): {n * .1:,.2f}   •   Chomesh (20%): {n * .2:,.2f}"


# ======================================================================== PLACES & HISTORY
@tool("Places & history", "Place finder (Tanach / Talmud)", "Coordinates and a map link for biblical and Talmudic places.", [{"name": "text", "label": "Place (blank = all)", "type": T}])
def places(a, ctx=None):
    t = _txt(a).strip().lower()
    return table(["Place", "מקום", "Lat", "Lon"], [[p[0], p[1], p[2], p[3]] for p in PLACES if not t or t in p[0].lower() or t in p[1]])


@tool("Places & history", "Eras timeline", "Tannaim, Amoraim, Geonim, Rishonim, Acharonim with years.", [])
def eras(a, ctx=None): return table(["Era", "From", "To"], [[e, f"{abs(s)} {'BCE' if s < 0 else 'CE'}", f"{abs(t)} {'BCE' if t < 0 else 'CE'}"] for e, s, t in ERAS])


@tool("Places & history", "Hebrew year ↔ civil year", "5787 ↔ 2026/27.", [{"name": "n", "label": "Year (Hebrew or civil)", "type": N}])
def year_convert(a, ctx=None):
    n = int(a.get("n") or 5787)
    return f"Hebrew {n} = {n - 3761}/{n - 3760} CE" if n > 3000 else f"{n} CE = Hebrew {n + 3760}/{n + 3761} ({H.int_to_hebrew(n + 3760)}/{H.int_to_hebrew(n + 3761)})"


class ToolInputError(ValueError):
    """A plain-English message for the user about what they typed."""


def _clean_args(t, args):
    """Accept what people really type: Hebrew-letter numbers (תשפ״ז, קכ), short Hebrew years (787 → 5787),
    commas in numbers, and dates as 7/11/2026 or 11.7.2026."""
    args = dict(args or {})
    kinds = {i["name"]: i.get("type") for i in t["inputs"]}
    for k, v in list(args.items()):
        kind = kinds.get(k)
        if not isinstance(v, str):
            continue
        v = v.strip()
        if kind == N and v:
            if re.search(r"[\u05d0-\u05ea]", v):
                n = H.g_standard(re.sub(r"[^\u05d0-\u05ea]", "", v))
                if k == "year" and n < 1000:
                    n += 5000
                v = str(n)
            v = v.replace(",", "")
            try:
                float(v)
            except ValueError:
                raise ToolInputError(f"“{args[k]}” is not a number - please type a number (or Hebrew letters like תשפ״ז).")
            if k == "year" and v.isdigit() and int(v) < 1000:
                v = str(int(v) + 5000)
        elif kind == D and v:
            m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", v)
            if m:
                mo, da = int(m.group(1)), int(m.group(2))
                if "." in v:
                    da, mo = mo, da  # 7.11.2026 = 7 November (European order)
                v = f"{m.group(3)}-{mo:02d}-{da:02d}"
            try:
                dt.date.fromisoformat(v)
            except ValueError:
                raise ToolInputError(f"“{args[k]}” is not a date - please pick a date (for example 2026-11-07).")
        args[k] = v
    return args


def run_tool(tid, args, ctx=None):
    for t in TOOLS:
        if t["id"] == tid:
            args = _clean_args(t, args)
            try:
                return t["fn"](args, ctx)
            except ToolInputError:
                raise
            except (ValueError, IndexError, OverflowError) as e:
                raise ToolInputError(f"That input doesn't work for this tool ({e}). Please check the numbers or date you typed.")
    raise KeyError(tid)


def tool_list():
    return [{k: v for k, v in t.items() if k != "fn"} for t in TOOLS]
