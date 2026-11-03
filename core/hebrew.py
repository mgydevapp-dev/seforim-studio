"""Hebrew text utilities: letters, nikud, gematria (many methods), ciphers,
numerals, keyboard layout, transliteration, tokenizing.  Pure Python, no deps."""
import re
import unicodedata

LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
TO_FINAL = {v: k for k, v in FINALS.items()}
ALL_LETTERS = LETTERS + "".join(FINALS)

# ---------------------------------------------------------------- regexes
RE_HTML = re.compile(r"<[^>]+>")
RE_FOOTNOTE = re.compile(r'<sup[^>]*footnote-marker[^>]*>.*?</sup>|<i[^>]*class="footnote"[^>]*>.*?</i>', re.S)
RE_TAAMIM = re.compile(r"[֑-ֽ֯׀׃׆]")      # cantillation + meteg, paseq, sof pasuq
RE_NIKUD = re.compile(r"[ְ-ׇּֿׁׂׅׄ]")  # vowels, dagesh, shin/sin dots
RE_ALL_MARKS = re.compile(r"[֑-ֽֿ-ׂׄ-ׇ]")
# a "word unit" inside Hebrew text: letters + marks + inner quotes (maqaf splits words)
RE_WORD_UNIT = re.compile(r"[א-ת֑-ֽֿ-ׂׄ-ׇ׳״\"'׳״]+")
RE_HEB = re.compile(r"[א-ת]")
RE_LAT = re.compile(r"[A-Za-z]")


def strip_html(s):
    if not s:
        return ""
    s = RE_FOOTNOTE.sub("", s)
    s = s.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    s = RE_HTML.sub("", s)
    return (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
             .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'").replace("&thinsp;", " "))


def remove_taamim(s):
    return RE_TAAMIM.sub("", s).replace("־", "־")


def remove_nikud(s):
    """Remove vowels AND cantillation, keep letters, maqaf, punctuation."""
    return RE_ALL_MARKS.sub("", s)


def letters_only(s):
    return "".join(ch for ch in s if "א" <= ch <= "ת")


def normalize_finals(s):
    return "".join(FINALS.get(c, c) for c in s)


def fix_final_letters(s):
    """Put correct final forms at end of every Hebrew word."""
    def fix(m):
        w = normalize_finals(m.group(0))
        if len(w) > 1 and w[-1] in TO_FINAL:
            w = w[:-1] + TO_FINAL[w[-1]]
        return w
    return re.sub(r"[א-ת]+", fix, s)


def has_hebrew(s):
    return bool(RE_HEB.search(s or ""))


def detect_lang(s):
    h, l = len(RE_HEB.findall(s or "")), len(RE_LAT.findall(s or ""))
    return "he" if h >= l and h > 0 else "en"


def word_units(text):
    """Yield (start, end, plain_word) for every Hebrew word in display text."""
    for m in RE_WORD_UNIT.finditer(text):
        p = letters_only(m.group(0))
        if p:
            yield m.start(), m.end(), p


def plain_words(text):
    return [p for _, _, p in word_units(text)]


def he_plain(text):
    return " ".join(plain_words(text))


# ---------------------------------------------------------------- gematria
STD = {"א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9, "י": 10,
       "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80, "צ": 90, "ק": 100,
       "ר": 200, "ש": 300, "ת": 400, "ך": 20, "ם": 40, "ן": 50, "ף": 80, "ץ": 90}
GADOL = dict(STD, **{"ך": 500, "ם": 600, "ן": 700, "ף": 800, "ץ": 900})
ORD = {c: i + 1 for i, c in enumerate(LETTERS)}
ORD.update({f: ORD[b] for f, b in FINALS.items()})
ORD_FINALS = dict(ORD, **{"ך": 23, "ם": 24, "ן": 25, "ף": 26, "ץ": 27})
ATBASH_MAP = {a: b for a, b in zip(LETTERS, LETTERS[::-1])}
ALBAM_MAP = {a: b for a, b in zip(LETTERS, LETTERS[11:] + LETTERS[:11])}
AVGAD_MAP = {a: LETTERS[(i + 1) % 22] for i, a in enumerate(LETTERS)}
REV_AVGAD = {v: k for k, v in AVGAD_MAP.items()}
# Achbi: split alphabet in two halves, atbash inside each half
_h1, _h2 = LETTERS[:11], LETTERS[11:]
ACHBI_MAP = dict(list(zip(_h1, _h1[::-1])) + list(zip(_h2, _h2[::-1])))
# Ayak Bachar: groups of letters sharing units digit (א-י-ק, ב-כ-ר, ...)
AYAK_GROUPS = ["איק", "בכר", "גלש", "דמת", "הנך", "וסם", "זען", "חפף", "טצץ"]
MILUI = {"א": "אלף", "ב": "בית", "ג": "גימל", "ד": "דלת", "ה": "הא", "ו": "ואו", "ז": "זין",
         "ח": "חית", "ט": "טית", "י": "יוד", "כ": "כף", "ל": "למד", "מ": "מם", "נ": "נון",
         "ס": "סמך", "ע": "עין", "פ": "פא", "צ": "צדי", "ק": "קוף", "ר": "ריש", "ש": "שין", "ת": "תו"}
LETTER_NAMES_EN = {"א": "Alef", "ב": "Bet", "ג": "Gimel", "ד": "Dalet", "ה": "He", "ו": "Vav",
                   "ז": "Zayin", "ח": "Chet", "ט": "Tet", "י": "Yud", "כ": "Kaf", "ל": "Lamed",
                   "מ": "Mem", "נ": "Nun", "ס": "Samech", "ע": "Ayin", "פ": "Pe", "צ": "Tzadi",
                   "ק": "Kuf", "ר": "Resh", "ש": "Shin", "ת": "Tav"}


def _sum(s, table):
    return sum(table.get(c, 0) for c in s)


def g_standard(s): return _sum(s, STD)
def g_gadol(s): return _sum(s, GADOL)
def g_ordinal(s): return _sum(s, ORD)
def g_ordinal_finals(s): return _sum(s, ORD_FINALS)


def g_katan(s):
    """Mispar katan: drop zeros from each letter's value."""
    return sum(int(str(STD[c]).rstrip("0") or 0) for c in s if c in STD)


def digital_root(n):
    return 0 if n == 0 else 1 + (n - 1) % 9


def g_katan_mispari(s):
    return digital_root(g_standard(s))


def g_kolel(s):
    """Standard + number of words (im hakolel)."""
    return g_standard(s) + max(1, len(plain_words(s)) or 1)


def g_im_haotiyot(s):
    return g_standard(s) + len(letters_only(s))


def g_atbash(s):
    return g_standard("".join(ATBASH_MAP.get(normalize_finals(c), c) for c in s))


def g_albam(s):
    return g_standard("".join(ALBAM_MAP.get(normalize_finals(c), c) for c in s))


def g_avgad(s):
    return g_standard("".join(AVGAD_MAP.get(normalize_finals(c), c) for c in s))


def g_kidmi(s):
    """Mispar kidmi (triangular): each letter = sum of all letters up to it."""
    vals = [STD[c] for c in LETTERS]
    tri = {c: sum(vals[:i + 1]) for i, c in enumerate(LETTERS)}
    return sum(tri.get(normalize_finals(c), 0) for c in s)


def g_bone(s):
    """Mispar bone'eh (building): running cumulative sum of the word."""
    total, run = 0, 0
    for c in letters_only(s):
        run += STD[c]
        total += run
    return total


def g_meshulash(s):
    """Mispar meshulash: cube of each letter value."""
    return sum(STD[c] ** 3 for c in letters_only(s))


def g_perati(s):
    """Mispar perati (square): square of each letter value."""
    return sum(STD[c] ** 2 for c in letters_only(s))


def g_milui(s):
    """Mispar shemi / milui: value of the spelled-out letter names."""
    return sum(g_standard(MILUI[normalize_finals(c)]) for c in letters_only(s))


def g_neelam(s):
    """Mispar ne'elam: hidden part of letter names (name minus first letter)."""
    return sum(g_standard(MILUI[normalize_finals(c)][1:]) for c in letters_only(s))


def g_reverse(s):
    """Mispar mesuraf? (reverse position value): ת=1 ... א=400 mapping by position."""
    rev = {c: STD[LETTERS[21 - i]] for i, c in enumerate(LETTERS)}
    return sum(rev.get(normalize_finals(c), 0) for c in s)


GEMATRIA_METHODS = {
    "Standard (Mispar Hechrachi)": g_standard,
    "Gadol (finals 500-900)": g_gadol,
    "Katan (small, no zeros)": g_katan,
    "Katan Mispari (digital root)": g_katan_mispari,
    "Ordinal (Siduri 1-22)": g_ordinal,
    "Ordinal with finals (1-27)": g_ordinal_finals,
    "Im HaKolel (+1 per word)": g_kolel,
    "Im HaOtiyot (+letters)": g_im_haotiyot,
    "Atbash value": g_atbash,
    "Albam value": g_albam,
    "Avgad value": g_avgad,
    "Kidmi (triangular)": g_kidmi,
    "Bone'eh (building)": g_bone,
    "Perati (squares)": g_perati,
    "Meshulash (cubes)": g_meshulash,
    "Milui / Shemi (letter names)": g_milui,
    "Ne'elam (hidden)": g_neelam,
}
# methods stored in the word index for fast searching (column names)
INDEXED_METHODS = {"Standard (Mispar Hechrachi)": "g_std", "Gadol (finals 500-900)": "g_gadol",
                   "Katan (small, no zeros)": "g_katan", "Ordinal (Siduri 1-22)": "g_ord"}


# ---------------------------------------------------------------- ciphers
def _map_text(s, mp):
    out = []
    for c in s:
        b = normalize_finals(c)
        out.append(mp.get(b, c))
    return fix_final_letters("".join(out))


def atbash(s): return _map_text(s, ATBASH_MAP)
def albam(s): return _map_text(s, ALBAM_MAP)
def avgad(s): return _map_text(s, AVGAD_MAP)
def reverse_avgad(s): return _map_text(s, REV_AVGAD)
def achbi(s): return _map_text(s, ACHBI_MAP)


def ayak_bachar(s):
    mp = {}
    for g in AYAK_GROUPS:
        for i, c in enumerate(g):
            mp[c] = g[(i + 1) % len(g)]
    out = "".join(mp.get(c, c) for c in s)
    return out


def milui_spell(s):
    return " ".join(MILUI[normalize_finals(c)] for c in letters_only(s))


# ---------------------------------------------------------------- numerals
def int_to_hebrew(n, geresh=True, thousands=True):
    """1-9999 -> Hebrew letters (e.g. 5787 -> ה׳תשפ״ז, 15 -> ט״ו)."""
    if n <= 0:
        return str(n)
    parts = []
    if n >= 1000 and thousands:
        parts.append(int_to_hebrew(n // 1000, geresh=False) + "׳")
        n %= 1000
        if n == 0:
            return parts[0]
    s = ""
    for val, ch in ((400, "ת"), (300, "ש"), (200, "ר"), (100, "ק")):
        while n >= val:
            s += ch
            n -= val
    if n == 15:
        s += "טו"; n = 0
    elif n == 16:
        s += "טז"; n = 0
    for val, ch in ((90, "צ"), (80, "פ"), (70, "ע"), (60, "ס"), (50, "נ"), (40, "מ"), (30, "ל"), (20, "כ"), (10, "י")):
        if n >= val:
            s += ch; n -= val
    if n:
        s += "אבגדהוזחט"[n - 1]
    if geresh:
        s = s + "׳" if len(s) == 1 else s[:-1] + "״" + s[-1]
    return "".join(parts) + s


def hebrew_to_int(s):
    s = s.replace("״", "").replace("׳", "'").replace('"', "")
    if "'" in s[:-1]:  # thousands marker
        k, rest = s.split("'", 1)
        return g_standard(k) * 1000 + g_standard(rest)
    return g_standard(s)


ONES_M = ["", "אחד", "שניים", "שלושה", "ארבעה", "חמישה", "שישה", "שבעה", "שמונה", "תשעה"]
ONES_F = ["", "אחת", "שתיים", "שלוש", "ארבע", "חמש", "שש", "שבע", "שמונה", "תשע"]
TENS = ["", "עשר", "עשרים", "שלושים", "ארבעים", "חמישים", "שישים", "שבעים", "שמונים", "תשעים"]
HUNDREDS = ["", "מאה", "מאתיים", "שלוש מאות", "ארבע מאות", "חמש מאות", "שש מאות", "שבע מאות", "שמונה מאות", "תשע מאות"]
THOUSANDS = {1: "אלף", 2: "אלפיים", 3: "שלושת אלפים", 4: "ארבעת אלפים", 5: "חמשת אלפים", 6: "ששת אלפים",
             7: "שבעת אלפים", 8: "שמונת אלפים", 9: "תשעת אלפים", 10: "עשרת אלפים"}


def number_to_words(n, feminine=True):
    """Spell a number 0-999999 in Hebrew words (feminine = counting form)."""
    if n == 0:
        return "אפס"
    ones = ONES_F if feminine else ONES_M
    words = []
    if n >= 1000:
        t = n // 1000
        words.append(THOUSANDS.get(t) or (number_to_words(t, False) + " אלף"))
        n %= 1000
    if n >= 100:
        words.append(HUNDREDS[n // 100]); n %= 100
    if 10 < n < 20:
        u = n - 10
        teen = (ONES_F[u] + " עשרה") if feminine else (ONES_M[u] + " עשר")
        if feminine and u == 2: teen = "שתים עשרה"
        if not feminine and u == 2: teen = "שנים עשר"
        words.append(teen); n = 0
    if n >= 10:
        words.append(TENS[n // 10]); n %= 10
    if n:
        words.append(ones[n])
    if len(words) > 1:
        words[-1] = "ו" + words[-1]
    return " ".join(words)


# ---------------------------------------------------------------- keyboard
EN_TO_HE = {"q": "/", "w": "'", "e": "ק", "r": "ר", "t": "א", "y": "ט", "u": "ו", "i": "ן", "o": "ם", "p": "פ",
            "a": "ש", "s": "ד", "d": "ג", "f": "כ", "g": "ע", "h": "י", "j": "ח", "k": "ל", "l": "ך", ";": "ף",
            "'": ",", "z": "ז", "x": "ס", "c": "ב", "v": "ה", "b": "נ", "n": "מ", "m": "צ", ",": "ת", ".": "ץ",
            "/": ".", "`": ";"}
HE_TO_EN = {v: k for k, v in EN_TO_HE.items() if len(v) == 1 and "א" <= v <= "ת"}


def en_layout_to_he(s):
    """Fix text typed on an English keyboard that should have been Hebrew."""
    return "".join(EN_TO_HE.get(c.lower(), c) if c.isalpha() or c in ";',./`" else c for c in s)


def he_layout_to_en(s):
    return "".join(HE_TO_EN.get(c, c) for c in s)


# ---------------------------------------------------------------- transliteration
TRANSLIT = {"א": "'", "ב": "v", "ג": "g", "ד": "d", "ה": "h", "ו": "v", "ז": "z", "ח": "ch", "ט": "t",
            "י": "y", "כ": "ch", "ך": "ch", "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s",
            "ע": "'", "פ": "f", "ף": "f", "צ": "tz", "ץ": "tz", "ק": "k", "ר": "r", "ש": "sh", "ת": "s"}
VOWELS = {"ְ": "e", "ֱ": "e", "ֲ": "a", "ֳ": "o", "ִ": "i", "ֵ": "ei",
          "ֶ": "e", "ַ": "a", "ָ": "o", "ֹ": "o", "ֻ": "u", "ׇ": "o"}


def transliterate(s, ashkenazi=True):
    """Rough Hebrew -> Latin transliteration (Ashkenazi or Sephardi pronunciation)."""
    s = RE_TAAMIM.sub("", unicodedata.normalize("NFD", s)).replace("־", " - ")
    # group into (letter, marks) clusters
    clusters, cur = [], None
    for c in s:
        if "א" <= c <= "ת":
            cur = [c, ""]; clusters.append(cur)
        elif cur is not None and "ְ" <= c <= "ׇ":
            cur[1] += c
        else:
            clusters.append([c, None]); cur = None
    out = []
    for i, (c, marks) in enumerate(clusters):
        if marks is None:
            out.append(c); continue
        first = i == 0 or clusters[i - 1][1] is None
        last = i + 1 >= len(clusters) or clusters[i + 1][1] is None
        prev_marks = clusters[i - 1][1] if not first else ""
        dag = "ּ" in marks
        t = TRANSLIT[c]
        if c in "אע": t = ""
        if c == "ב" and dag: t = "b"
        if c in "כך" and dag: t = "k"
        if c == "פ" and dag: t = "p"
        if c == "ת" and (dag or not ashkenazi): t = "t"
        if c == "ש" and "ׂ" in marks: t = "s"
        if c == "ה" and last and not dag: t = "h"
        vowel = ""
        for m in marks:
            if m in VOWELS:
                vowel = VOWELS[m]
                if not ashkenazi and m == "ָ": vowel = "a"
                if not ashkenazi and m == "ֵ": vowel = "e"
                if m == "ְ": vowel = "e" if first else ""
        if c == "ו" and "ֹ" in marks and not first: t, vowel = "", "o"
        if c == "ו" and dag and not first and not vowel: t, vowel = "", "u"
        if c == "י" and not vowel and prev_marks and any(v in prev_marks for v in "ִֵ"):
            t = "" if (prev_marks and "ִ" in prev_marks) else "i"
        if c == "ו" and not vowel and not dag and prev_marks and "ֹ" in prev_marks and not first:
            t = ""
        out.append(t + vowel)
    return re.sub(r"\s+", " ", "".join(out)).strip()


EN_PHON = [("sh", "ש"), ("ch", "ח"), ("tz", "צ"), ("ts", "צ"), ("kh", "ח"), ("th", "ת"),
           ("a", "א"), ("b", "ב"), ("c", "ק"), ("d", "ד"), ("e", ""), ("f", "פ"), ("g", "ג"), ("h", "ה"),
           ("i", "י"), ("j", "ג׳"), ("k", "ק"), ("l", "ל"), ("m", "מ"), ("n", "נ"), ("o", "ו"), ("p", "פ"),
           ("q", "ק"), ("r", "ר"), ("s", "ס"), ("t", "ט"), ("u", "ו"), ("v", "ו"), ("w", "ו"), ("x", "קס"),
           ("y", "י"), ("z", "ז")]


def english_to_hebrew_letters(s):
    """Phonetic English -> Hebrew letters (for names), e.g. 'Moshe' -> 'מושה'."""
    out_words = []
    for word in re.split(r"(\s+)", s):
        if not word.strip():
            out_words.append(word); continue
        w, res, i = word.lower(), "", 0
        while i < len(w):
            for k, v in EN_PHON:
                if w.startswith(k, i):
                    if k == "a" and i > 0: v = ""
                    if k == "e" and i == len(w) - 1: v = "ה"
                    if k == "a" and i == len(w) - 1 and len(w) > 1: v = "ה"
                    res += v; i += len(k); break
            else:
                res += w[i]; i += 1
        out_words.append(fix_final_letters(res))
    return "".join(out_words)


# ---------------------------------------------------------------- misc helpers
def letter_frequency(s):
    from collections import Counter
    return Counter(normalize_finals(letters_only(s)))


def roshei_teivos(s):
    return "".join(w[0] for w in plain_words(s))


def sofei_teivos(s):
    return "".join(w[-1] for w in plain_words(s))


def to_gershayim(s):
    """Convert ASCII quotes inside Hebrew abbreviations to proper ״ and ׳."""
    s = re.sub(r'(?<=[א-ת])"(?=[א-ת])', "״", s)
    return re.sub(r"(?<=[א-ת])'", "׳", s)


def from_gershayim(s):
    return s.replace("״", '"').replace("׳", "'")


def is_palindrome(w):
    w = normalize_finals(letters_only(w))
    return len(w) > 1 and w == w[::-1]


def mirror_text(s):
    return s[::-1]


def add_rlm(s):
    """Add right-to-left marks around neutral punctuation so it renders correctly."""
    return re.sub(r"([.,:;!?()\-])", "‏\\1‏", s)
