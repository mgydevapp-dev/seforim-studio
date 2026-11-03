"""Traditional ordering and Hebrew names used to sort the library neatly."""

TOP_ORDER = ["Tanakh", "Mishnah", "Tosefta", "Talmud", "Midrash", "Halakhah", "Kabbalah", "Liturgy",
             "Jewish Thought", "Chasidut", "Musar", "Responsa", "Second Temple", "Reference"]

SUB_ORDER = ["Torah", "Prophets", "Writings", "Targum", "Rishonim on Tanakh", "Acharonim on Tanakh",
             "Bavli", "Yerushalmi", "Seder Zeraim", "Seder Moed", "Seder Nashim", "Seder Nezikin",
             "Seder Kodashim", "Seder Tahorot", "Mishneh Torah", "Shulchan Arukh", "Tur"]

BOOK_ORDER = [
    # Tanakh
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "I Samuel", "II Samuel",
    "I Kings", "II Kings", "Isaiah", "Jeremiah", "Ezekiel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", "Psalms", "Proverbs", "Job",
    "Song of Songs", "Ruth", "Lamentations", "Ecclesiastes", "Esther", "Daniel", "Ezra", "Nehemiah",
    "I Chronicles", "II Chronicles",
    # Shas (Bavli / Mishnah order)
    "Berakhot", "Peah", "Demai", "Kilayim", "Sheviit", "Terumot", "Maasrot", "Maaser Sheni", "Challah", "Orlah",
    "Bikkurim", "Shabbat", "Eruvin", "Pesachim", "Shekalim", "Yoma", "Sukkah", "Beitzah", "Rosh Hashanah",
    "Taanit", "Megillah", "Moed Katan", "Chagigah", "Yevamot", "Ketubot", "Nedarim", "Nazir", "Sotah", "Gittin",
    "Kiddushin", "Bava Kamma", "Bava Metzia", "Bava Batra", "Sanhedrin", "Makkot", "Shevuot", "Eduyot",
    "Avodah Zarah", "Pirkei Avot", "Horayot", "Zevachim", "Menachot", "Chullin", "Bekhorot", "Arakhin",
    "Temurah", "Keritot", "Meilah", "Tamid", "Middot", "Kinnim", "Kelim", "Oholot", "Negaim", "Parah",
    "Tahorot", "Mikvaot", "Niddah", "Makhshirin", "Zavim", "Tevul Yom", "Yadayim", "Oktzin",
]
BOOK_RANK = {b: i for i, b in enumerate(BOOK_ORDER)}

HE_NAMES = {
    "Tanakh": "תנ״ך", "Torah": "תורה", "Prophets": "נביאים", "Writings": "כתובים", "Mishnah": "משנה",
    "Tosefta": "תוספתא", "Talmud": "תלמוד", "Bavli": "בבלי", "Yerushalmi": "ירושלמי", "Midrash": "מדרש",
    "Halakhah": "הלכה", "Kabbalah": "קבלה", "Liturgy": "תפילה", "Jewish Thought": "מחשבת ישראל",
    "Chasidut": "חסידות", "Musar": "מוסר", "Responsa": "שו״ת", "Second Temple": "בית שני", "Reference": "עיון",
    "Targum": "תרגום", "Commentary": "מפרשים", "Rishonim on Tanakh": "ראשונים על התנ״ך",
    "Acharonim on Tanakh": "אחרונים על התנ״ך", "Seder Zeraim": "סדר זרעים", "Seder Moed": "סדר מועד",
    "Seder Nashim": "סדר נשים", "Seder Nezikin": "סדר נזיקין", "Seder Kodashim": "סדר קדשים",
    "Seder Tahorot": "סדר טהרות", "Shulchan Arukh": "שולחן ערוך", "Mishneh Torah": "משנה תורה",
    "Genesis": "בראשית", "Exodus": "שמות", "Leviticus": "ויקרא", "Numbers": "במדבר", "Deuteronomy": "דברים",
    "Joshua": "יהושע", "Judges": "שופטים", "I Samuel": "שמואל א", "II Samuel": "שמואל ב", "I Kings": "מלכים א",
    "II Kings": "מלכים ב", "Isaiah": "ישעיהו", "Jeremiah": "ירמיהו", "Ezekiel": "יחזקאל", "Hosea": "הושע",
    "Joel": "יואל", "Amos": "עמוס", "Obadiah": "עובדיה", "Jonah": "יונה", "Micah": "מיכה", "Nahum": "נחום",
    "Habakkuk": "חבקוק", "Zephaniah": "צפניה", "Haggai": "חגי", "Zechariah": "זכריה", "Malachi": "מלאכי",
    "Psalms": "תהילים", "Proverbs": "משלי", "Job": "איוב", "Song of Songs": "שיר השירים", "Ruth": "רות",
    "Lamentations": "איכה", "Ecclesiastes": "קהלת", "Esther": "אסתר", "Daniel": "דניאל", "Ezra": "עזרא",
    "Nehemiah": "נחמיה", "I Chronicles": "דברי הימים א", "II Chronicles": "דברי הימים ב",
    "Berakhot": "ברכות", "Shabbat": "שבת", "Eruvin": "עירובין", "Pesachim": "פסחים", "Shekalim": "שקלים",
    "Yoma": "יומא", "Sukkah": "סוכה", "Beitzah": "ביצה", "Rosh Hashanah": "ראש השנה", "Taanit": "תענית",
    "Megillah": "מגילה", "Moed Katan": "מועד קטן", "Chagigah": "חגיגה", "Yevamot": "יבמות", "Ketubot": "כתובות",
    "Nedarim": "נדרים", "Nazir": "נזיר", "Sotah": "סוטה", "Gittin": "גיטין", "Kiddushin": "קידושין",
    "Bava Kamma": "בבא קמא", "Bava Metzia": "בבא מציעא", "Bava Batra": "בבא בתרא", "Sanhedrin": "סנהדרין",
    "Makkot": "מכות", "Shevuot": "שבועות", "Avodah Zarah": "עבודה זרה", "Horayot": "הוריות",
    "Zevachim": "זבחים", "Menachot": "מנחות", "Chullin": "חולין", "Bekhorot": "בכורות", "Arakhin": "ערכין",
    "Temurah": "תמורה", "Keritot": "כריתות", "Meilah": "מעילה", "Tamid": "תמיד", "Niddah": "נדה",
    "Pirkei Avot": "פרקי אבות",
}


def sort_key(name, fallback_index=0):
    if name in TOP_ORDER:
        return (0, TOP_ORDER.index(name), name)
    if name in SUB_ORDER:
        return (1, SUB_ORDER.index(name), name)
    for prefix in ("Mishnah ", "Jerusalem Talmud ", "Tosefta "):
        if name.startswith(prefix) and name[len(prefix):] in BOOK_RANK:
            return (2, BOOK_RANK[name[len(prefix):]], name)
    if name in BOOK_RANK:
        return (2, BOOK_RANK[name], name)
    for base, r in BOOK_RANK.items():  # "Rashi on Genesis" sorts with Genesis
        if name.endswith(" on " + base) or name.endswith(" " + base):
            return (3, r, name)
    return (4, fallback_index, name.lower())


def he_name(name):
    from .he_names import he_name as _h
    return _h(name)
