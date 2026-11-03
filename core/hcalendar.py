"""Offline Jewish calendar: Hebrew<->Gregorian, holidays, molad, omer, yahrzeit,
daf yomi, zmanim (NOAA solar math). Parasha uses the optional 'pyluach' package."""
import datetime as dt
import math
from .hebrew import int_to_hebrew

EPOCH = -1373427  # R.D. of 1 Tishrei AM 1
NISAN, IYYAR, SIVAN, TAMMUZ, AV, ELUL, TISHREI, CHESHVAN, KISLEV, TEVET, SHEVAT, ADAR, ADAR2 = range(1, 14)
MONTHS_EN = {1: "Nisan", 2: "Iyar", 3: "Sivan", 4: "Tammuz", 5: "Av", 6: "Elul", 7: "Tishrei",
             8: "Cheshvan", 9: "Kislev", 10: "Tevet", 11: "Shevat", 12: "Adar", 13: "Adar II"}
MONTHS_HE = {1: "ניסן", 2: "אייר", 3: "סיון", 4: "תמוז", 5: "אב", 6: "אלול", 7: "תשרי",
             8: "חשון", 9: "כסלו", 10: "טבת", 11: "שבט", 12: "אדר", 13: "אדר ב׳"}
DAYS_EN = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Shabbos"]
DAYS_HE = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]


def is_leap(y): return (7 * y + 1) % 19 < 7
def last_month(y): return 13 if is_leap(y) else 12


def _elapsed(y):
    months = (235 * y - 234) // 19
    parts = 12084 + 13753 * months
    day = 29 * months + parts // 25920
    return day + 1 if (3 * (day + 1)) % 7 < 3 else day


def _correction(y):
    ny0, ny1, ny2 = _elapsed(y - 1), _elapsed(y), _elapsed(y + 1)
    if ny2 - ny1 == 356: return 2
    if ny1 - ny0 == 382: return 1
    return 0


def new_year(y): return EPOCH + _elapsed(y) + _correction(y)
def days_in_year(y): return new_year(y + 1) - new_year(y)
def long_cheshvan(y): return days_in_year(y) in (355, 385)
def short_kislev(y): return days_in_year(y) in (353, 383)


def month_length(m, y):
    if m in (2, 4, 6, 10, 13) or (m == 12 and not is_leap(y)) or (m == 8 and not long_cheshvan(y)) \
            or (m == 9 and short_kislev(y)):
        return 29
    return 30


def to_fixed(y, m, d):
    nd = new_year(y) + d - 1
    if m < 7:
        for mm in range(7, last_month(y) + 1): nd += month_length(mm, y)
        for mm in range(1, m): nd += month_length(mm, y)
    else:
        for mm in range(7, m): nd += month_length(mm, y)
    return nd


def from_fixed(rd):
    y = int((rd - EPOCH) / (35975351 / 98496)) + 1
    while new_year(y) > rd: y -= 1
    while new_year(y + 1) <= rd: y += 1
    m = 7 if rd < to_fixed(y, 1, 1) else 1
    while rd > to_fixed(y, m, month_length(m, y)): m += 1
    return y, m, rd - to_fixed(y, m, 1) + 1


def greg_to_heb(d: dt.date): return from_fixed(d.toordinal())
def heb_to_greg(y, m, d): return dt.date.fromordinal(to_fixed(y, m, d))


def month_name(m, y, hebrew=False):
    if m == 12 and is_leap(y): return "אדר א׳" if hebrew else "Adar I"
    return (MONTHS_HE if hebrew else MONTHS_EN)[m]


def format_hebrew(y, m, d, hebrew=True):
    if hebrew:
        return f"{int_to_hebrew(d)} {month_name(m, y, True)} {int_to_hebrew(y)}"
    return f"{d} {month_name(m, y)} {y}"


def year_info(y):
    n = days_in_year(y)
    kind = {353: "deficient (chaseira)", 354: "regular (kesidra)", 355: "complete (shleima)",
            383: "deficient (chaseira)", 384: "regular (kesidra)", 385: "complete (shleima)"}[n]
    rh = dt.date.fromordinal(new_year(y))
    pesach = heb_to_greg(y, 1, 15)
    return {"year": y, "hebrew": int_to_hebrew(y), "leap": is_leap(y), "days": n, "type": kind,
            "rosh_hashana": rh, "rosh_hashana_day": DAYS_EN[(rh.weekday() + 1) % 7],
            "pesach_day": DAYS_EN[(pesach.weekday() + 1) % 7],
            "cycle_year": (y - 1) % 19 + 1, "shmita": y % 7 == 0}


def weekday_index(d): return (d.weekday() + 1) % 7  # 0=Sunday


def holidays(y, israel=False):
    """Return sorted list of (gregorian date, english, hebrew) for Hebrew year y."""
    H = []
    def add(m, d, en, he, n=1):
        for i in range(n):
            H.append((heb_to_greg(y, m, d) + dt.timedelta(days=i), en + (f" {i+1}" if n > 1 else ""), he))
    add(7, 1, "Rosh Hashana", "ראש השנה", 2)
    g = heb_to_greg(y, 7, 3)
    add(7, 3 if weekday_index(g) != 6 else 4, "Tzom Gedaliah", "צום גדליה")
    add(7, 10, "Yom Kippur", "יום כיפור")
    add(7, 15, "Sukkos", "סוכות", 1 if israel else 2)
    add(7, 17 if not israel else 16, "Chol HaMoed Sukkos", "חול המועד סוכות", 4 if not israel else 5)
    add(7, 21, "Hoshana Rabba", "הושענא רבה")
    add(7, 22, "Shemini Atzeres" + (" / Simchas Torah" if israel else ""), "שמיני עצרת")
    if not israel: add(7, 23, "Simchas Torah", "שמחת תורה")
    chan = heb_to_greg(y, 9, 25)
    for i in range(8): H.append((chan + dt.timedelta(days=i), f"Chanukah day {i+1}", f"חנוכה נר {int_to_hebrew(i+1)}"))
    add(10, 10, "Asara B'Teves", "עשרה בטבת")
    add(11, 15, "Tu B'Shvat", "ט״ו בשבט")
    am = 13 if is_leap(y) else 12
    if is_leap(y): add(12, 14, "Purim Katan", "פורים קטן")
    p = heb_to_greg(y, am, 13)
    te = p if weekday_index(p) != 6 else p - dt.timedelta(days=2)
    H.append((te, "Taanis Esther", "תענית אסתר"))
    add(am, 14, "Purim", "פורים")
    add(am, 15, "Shushan Purim", "שושן פורים")
    add(1, 14, "Erev Pesach", "ערב פסח")
    add(1, 15, "Pesach", "פסח", 1 if israel else 2)
    add(1, 16 if israel else 17, "Chol HaMoed Pesach", "חול המועד פסח", 5 if israel else 4)
    add(1, 21, "Shvi'i shel Pesach", "שביעי של פסח")
    if not israel: add(1, 22, "Acharon shel Pesach", "אחרון של פסח")
    add(1, 27, "Yom HaShoah", "יום השואה")
    add(2, 14, "Pesach Sheni", "פסח שני")
    add(2, 18, "Lag BaOmer", "ל״ג בעומר")
    add(2, 28, "Yom Yerushalayim", "יום ירושלים")
    add(3, 6, "Shavuos", "שבועות", 1 if israel else 2)
    t17 = heb_to_greg(y, 4, 17)
    H.append((t17 + dt.timedelta(days=1 if weekday_index(t17) == 6 else 0), "Shiva Asar B'Tammuz", "שבעה עשר בתמוז"))
    t9 = heb_to_greg(y, 5, 9)
    H.append((t9 + dt.timedelta(days=1 if weekday_index(t9) == 6 else 0), "Tisha B'Av", "תשעה באב"))
    add(5, 15, "Tu B'Av", "ט״ו באב")
    # Rosh Chodesh
    for m in list(range(7, last_month(y) + 1)) + list(range(1, 7)):
        if m == 7: continue
        prev = m - 1 if m != 1 else last_month(y)
        if m == 8: prev = 7
        if month_length(prev, y) == 30:
            H.append((heb_to_greg(y, prev, 30), f"Rosh Chodesh {month_name(m, y)}", f"ראש חודש {month_name(m, y, True)}"))
        H.append((heb_to_greg(y, m, 1), f"Rosh Chodesh {month_name(m, y)}", f"ראש חודש {month_name(m, y, True)}"))
    return sorted(H)


def holiday_on(d, israel=False):
    y = greg_to_heb(d)[0]
    return [(en, he) for gd, en, he in holidays(y, israel) if gd == d]


def omer_day(d):
    y, m, dd = greg_to_heb(d)
    n = d.toordinal() - to_fixed(y, 1, 16) + 1
    return n if 1 <= n <= 49 else 0


def omer_text(n):
    if not n: return ""
    w, r = divmod(n, 7)
    he = f"היום {int_to_hebrew(n, geresh=False)} יום" if n > 1 else "היום יום אחד"
    if n >= 7:
        he += f" שהם {w} שבועות" + (f" ו{r} ימים" if r else "")
    sefiros = ["חסד", "גבורה", "תפארת", "נצח", "הוד", "יסוד", "מלכות"]
    return f"Day {n} ({w} weeks, {r} days) — {he} לעומר — {sefiros[(n-1)%7]} שב{sefiros[(n-1)//7]}"


def molad(y, m):
    """Molad of Hebrew month -> (weekday name, hours, minutes, chalakim) Jerusalem time (from 6pm)."""
    from fractions import Fraction as F
    yy = y + 1 if m < 7 else y
    months = m - 7 + (235 * yy - 234) // 19
    moment = F(EPOCH) - F(876, 25920) + months * (29 + F(1, 2) + F(793, 25920))
    day = math.floor(moment)
    parts = round((moment - day) * 25920)          # 1080 parts per hour, midnight-based
    hours, rem = divmod(parts, 1080)
    minutes, ch = divmod(rem, 18)
    g = dt.date.fromordinal(day)
    return DAYS_EN[weekday_index(g)], g, hours, minutes, ch


def molad_text(y, m):
    wd, g, h, mi, ch = molad(y, m)
    ampm = "AM" if h < 12 else "PM"
    return f"{wd} {g:%b %d %Y}, {(h % 12) or 12}:{mi:02d} {ampm} and {ch} chalakim (Jerusalem mean time)"


def yahrzeit(death_greg: dt.date, after_sunset=False, years=10):
    """Return list of upcoming yahrzeit Gregorian dates."""
    d = death_greg + dt.timedelta(days=1 if after_sunset else 0)
    hy, hm, hd = greg_to_heb(d)
    out, cur = [], greg_to_heb(dt.date.today())[0]
    for y in range(cur, cur + years):
        m, day = hm, hd
        if hm == 13 and not is_leap(y): m = 12
        if hm == 12 and is_leap(y) and not is_leap(hy): m = 13
        if hm == 8 and hd == 30 and not long_cheshvan(y): m, day = 9, 1
        if hm == 9 and hd == 30 and short_kislev(y): m, day = 10, 1
        if hm == 12 and hd == 30 and not is_leap(y): m, day = 1, 1
        if day > month_length(m, y): day = month_length(m, y)
        g = heb_to_greg(y, m, day)
        if g >= dt.date.today(): out.append((g, format_hebrew(y, m, day)))
    return out


def hebrew_birthday(birth: dt.date, after_sunset=False, years=10):
    return yahrzeit(birth, after_sunset, years)


def bar_mitzvah(birth: dt.date, after_sunset=False, age=13):
    d = birth + dt.timedelta(days=1 if after_sunset else 0)
    hy, hm, hd = greg_to_heb(d)
    y = hy + age
    m = hm
    if hm == 13 and not is_leap(y): m = 12
    if hm == 12 and is_leap(y) and not is_leap(hy): m = 13
    day = min(hd, month_length(m, y))
    return heb_to_greg(y, m, day), format_hebrew(y, m, day)


# ---------------------------------------------------------------- daf yomi
SHAS = [("Berakhot", 2, 64), ("Shabbat", 2, 157), ("Eruvin", 2, 105), ("Pesachim", 2, 121), ("Shekalim", 2, 22),
        ("Yoma", 2, 88), ("Sukkah", 2, 56), ("Beitzah", 2, 40), ("Rosh Hashanah", 2, 35), ("Taanit", 2, 31),
        ("Megillah", 2, 32), ("Moed Katan", 2, 29), ("Chagigah", 2, 27), ("Yevamot", 2, 122), ("Ketubot", 2, 112),
        ("Nedarim", 2, 91), ("Nazir", 2, 66), ("Sotah", 2, 49), ("Gittin", 2, 90), ("Kiddushin", 2, 82),
        ("Bava Kamma", 2, 119), ("Bava Metzia", 2, 119), ("Bava Batra", 2, 176), ("Sanhedrin", 2, 113),
        ("Makkot", 2, 24), ("Shevuot", 2, 49), ("Avodah Zarah", 2, 76), ("Horayot", 2, 14), ("Zevachim", 2, 120),
        ("Menachot", 2, 110), ("Chullin", 2, 142), ("Bekhorot", 2, 61), ("Arakhin", 2, 34), ("Temurah", 2, 34),
        ("Keritot", 2, 28), ("Meilah", 2, 22), ("Kinnim", 23, 25), ("Tamid", 26, 33), ("Middot", 34, 37),
        ("Niddah", 2, 73)]
SHAS_HE = ["ברכות", "שבת", "עירובין", "פסחים", "שקלים", "יומא", "סוכה", "ביצה", "ראש השנה", "תענית", "מגילה",
           "מועד קטן", "חגיגה", "יבמות", "כתובות", "נדרים", "נזיר", "סוטה", "גיטין", "קידושין", "בבא קמא",
           "בבא מציעא", "בבא בתרא", "סנהדרין", "מכות", "שבועות", "עבודה זרה", "הוריות", "זבחים", "מנחות", "חולין",
           "בכורות", "ערכין", "תמורה", "כריתות", "מעילה", "קינים", "תמיד", "מדות", "נדה"]
CYCLE_DAYS = sum(b - a + 1 for _, a, b in SHAS)
DAF_CYCLE14_START = dt.date(2020, 1, 5)


def daf_yomi(d: dt.date):
    n = (d - DAF_CYCLE14_START).days % CYCLE_DAYS
    for i, (name, a, b) in enumerate(SHAS):
        cnt = b - a + 1
        if n < cnt:
            daf = a + n
            return name, daf, f"{SHAS_HE[i]} {int_to_hebrew(daf)}"
        n -= cnt


# ---------------------------------------------------------------- zmanim
def _sun_time(date, lat, lon, tz_hours, zenith, rising):
    """NOAA algorithm. Returns local datetime or None (polar)."""
    N = date.timetuple().tm_yday
    lng_hour = lon / 15.0
    t = N + ((6 if rising else 18) - lng_hour) / 24
    M = 0.9856 * t - 3.289
    L = (M + 1.916 * math.sin(math.radians(M)) + 0.020 * math.sin(math.radians(2 * M)) + 282.634) % 360
    RA = math.degrees(math.atan(0.91764 * math.tan(math.radians(L)))) % 360
    RA = (RA + (math.floor(L / 90) * 90 - math.floor(RA / 90) * 90)) / 15
    sin_dec = 0.39782 * math.sin(math.radians(L))
    cos_dec = math.cos(math.asin(sin_dec))
    cos_h = (math.cos(math.radians(zenith)) - sin_dec * math.sin(math.radians(lat))) / (cos_dec * math.cos(math.radians(lat)))
    if cos_h > 1 or cos_h < -1:
        return None
    H = (360 - math.degrees(math.acos(cos_h))) if rising else math.degrees(math.acos(cos_h))
    T = H / 15 + RA - 0.06571 * t - 6.622
    UT = (T - lng_hour) % 24
    local = (UT + tz_hours) % 24
    return dt.datetime.combine(date, dt.time()) + dt.timedelta(hours=local)


def zmanim(date, lat, lon, tz_hours, candle_minutes=18):
    sr = _sun_time(date, lat, lon, tz_hours, 90.833, True)
    ss = _sun_time(date, lat, lon, tz_hours, 90.833, False)
    alos = _sun_time(date, lat, lon, tz_hours, 106.1, True)
    misheyakir = _sun_time(date, lat, lon, tz_hours, 101.0, True)
    tzeis = _sun_time(date, lat, lon, tz_hours, 98.5, False)
    out = {}
    if not (sr and ss):
        return {"Note": "Sun does not rise/set on this date at this location"}
    hour = (ss - sr) / 12
    mga_start, mga_end = sr - dt.timedelta(minutes=72), ss + dt.timedelta(minutes=72)
    mga_hour = (mga_end - mga_start) / 12
    out["Alos HaShachar (16.1°)"] = alos
    out["Misheyakir (11°)"] = misheyakir
    out["Netz / Sunrise"] = sr
    out["Sof Zman Shema (MGA)"] = mga_start + 3 * mga_hour
    out["Sof Zman Shema (GRA)"] = sr + 3 * hour
    out["Sof Zman Tefillah (MGA)"] = mga_start + 4 * mga_hour
    out["Sof Zman Tefillah (GRA)"] = sr + 4 * hour
    out["Chatzos"] = sr + 6 * hour
    out["Mincha Gedola"] = sr + 6.5 * hour
    out["Mincha Ketana"] = sr + 9.5 * hour
    out["Plag HaMincha"] = sr + 10.75 * hour
    out["Candle lighting"] = ss - dt.timedelta(minutes=candle_minutes)
    out["Shkia / Sunset"] = ss
    out["Tzeis HaKochavim (8.5°)"] = tzeis
    out["Rabbeinu Tam (72 min)"] = ss + dt.timedelta(minutes=72)
    out["Shaah Zmanis (GRA)"] = hour
    return out


def parasha(d: dt.date, israel=False, hebrew=False):
    """Weekly parasha for the Shabbos on/after d (needs pyluach)."""
    try:
        from pyluach import dates, parshios
        sat = d + dt.timedelta(days=(5 - d.weekday()) % 7)
        return parshios.getparsha_string(dates.GregorianDate(sat.year, sat.month, sat.day),
                                         israel=israel, hebrew=hebrew) or ("No regular parasha (Yom Tov)" if not hebrew else "שבת יום טוב")
    except Exception:
        return "(install 'pyluach' for parasha: pip install pyluach)"
