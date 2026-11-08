"""English → Hebrew names for categories, seforim and commentators, with a compositional resolver
("Rashi on Genesis" → "רש״י על בראשית", "Mishnah Berakhot" → "משנה ברכות").
Exact official Hebrew titles (from the Sefaria schemas, downloaded once) always take priority."""
import re

NAMES = {
    # ---------------- top categories / structure
    "Tanakh": "תנ״ך", "Torah": "תורה", "Prophets": "נביאים", "Writings": "כתובים", "Mishnah": "משנה", "Tosefta": "תוספתא",
    "Talmud": "תלמוד", "Bavli": "בבלי", "Yerushalmi": "ירושלמי", "Midrash": "מדרש", "Halakhah": "הלכה", "Kabbalah": "קבלה",
    "Liturgy": "תפילה", "Jewish Thought": "מחשבת ישראל", "Chasidut": "חסידות", "Musar": "מוסר", "Responsa": "שו״ת",
    "Second Temple": "ספרות בית שני", "Reference": "ספרי עיון", "Targum": "תרגום", "Aramaic Targum": "תרגום ארמי",
    "Commentary": "מפרשים", "Comment": "הערות", "Modern": "מחברים בני זמננו", "Modern Texts": "טקסטים מודרניים", "Rishonim": "ראשונים",
    "Acharonim": "אחרונים", "Geonim": "גאונים", "Early Works": "חיבורים קדומים", "Introduction": "הקדמה", "Guides": "מדריכים",
    "Rishonim on Tanakh": "ראשונים על התנ״ך", "Acharonim on Tanakh": "אחרונים על התנ״ך", "Modern Commentary on Tanakh": "פרשנות מודרנית על התנ״ך",
    "Rishonim on Talmud": "ראשונים על התלמוד", "Acharonim on Talmud": "אחרונים על התלמוד", "Modern Commentary on Talmud": "פרשנות מודרנית על התלמוד",
    "Rishonim on Mishnah": "ראשונים על המשנה", "Acharonim on Mishnah": "אחרונים על המשנה", "Modern Commentary on Mishnah": "פרשנות מודרנית על המשנה",
    "Minor Tractates": "מסכתות קטנות", "Commentary on Minor Tractates": "מפרשים על מסכתות קטנות", "Aggadah": "אגדה",
    "Midrash Rabbah": "מדרש רבה", "Haggadah": "הגדה של פסח", "Siddur": "סידור", "Piyutim": "פיוטים", "High Holidays": "ימים נוראים",
    "Other Liturgy Works": "ספרי תפילה נוספים", "Other Chasidut Works": "ספרי חסידות נוספים", "Other Kabbalah Works": "ספרי קבלה נוספים",
    "Encyclopedic Works": "אנציקלופדיות", "Dictionary": "מילונים", "Grammar": "דקדוק", "Apocrypha": "ספרים חיצוניים",
    "Sifrei Mitzvot": "ספרי מצוות", "Variants": "נוסחאות", "Brief Commentary": "פירוש קצר", "English Explanation of Mishnah": "ביאור אנגלי למשנה",
    "German Commentary": "פירוש בגרמנית", "Lieberman Edition": "מהדורת ליברמן", "Vilna Edition": "דפוס וילנא", "Seder Mishnah": "סדר המשנה",
    "Haggahot": "הגהות", "Haggahot and Marei Mekomot": "הגהות ומראי מקומות", "Nuschaot from Manuscripts": "נוסחאות מכתבי יד",
    "New Nuschah": "נוסח חדש", "Gra's Nuschah": "נוסח הגר״א", "Daf Shevui": "דף שבועי", "Josephus": "יוסף בן מתתיהו", "Philo": "פילון",
    "Rabbinic Authority Series": "סדרת סמכות רבנית", "Contemporary Halakhic Problems": "בעיות הלכתיות בזמננו", "Gray Matter": "גריי מאטר",
    # orders & books of Mishneh Torah
    "Seder Zeraim": "סדר זרעים", "Seder Moed": "סדר מועד", "Seder Nashim": "סדר נשים", "Seder Nezikin": "סדר נזיקין",
    "Seder Kodashim": "סדר קדשים", "Seder Tahorot": "סדר טהרות", "Mishneh Torah": "משנה תורה", "Sefer Madda": "ספר המדע",
    "Sefer Ahavah": "ספר אהבה", "Sefer Zemanim": "ספר זמנים", "Sefer Nashim": "ספר נשים", "Sefer Kedushah": "ספר קדושה",
    "Sefer Haflaah": "ספר הפלאה", "Sefer Zeraim": "ספר זרעים", "Sefer Avodah": "ספר עבודה", "Sefer Korbanot": "ספר קרבנות",
    "Sefer Taharah": "ספר טהרה", "Sefer Nezikim": "ספר נזיקין", "Sefer Kinyan": "ספר קנין", "Sefer Mishpatim": "ספר משפטים",
    "Sefer Shoftim": "ספר שופטים", "Shulchan Arukh": "שולחן ערוך", "Tur": "טור", "Orach Chayim": "אורח חיים", "Yoreh De'ah": "יורה דעה",
    "Even HaEzer": "אבן העזר", "Choshen Mishpat": "חושן משפט", "Shulchan Arukh HaRav": "שולחן ערוך הרב",
    # ---------------- Tanakh books
    "Genesis": "בראשית", "Exodus": "שמות", "Leviticus": "ויקרא", "Numbers": "במדבר", "Deuteronomy": "דברים", "Joshua": "יהושע",
    "Judges": "שופטים", "I Samuel": "שמואל א", "II Samuel": "שמואל ב", "I Kings": "מלכים א", "II Kings": "מלכים ב", "Isaiah": "ישעיהו",
    "Jeremiah": "ירמיהו", "Ezekiel": "יחזקאל", "Hosea": "הושע", "Joel": "יואל", "Amos": "עמוס", "Obadiah": "עובדיה", "Jonah": "יונה",
    "Micah": "מיכה", "Nahum": "נחום", "Habakkuk": "חבקוק", "Zephaniah": "צפניה", "Haggai": "חגי", "Zechariah": "זכריה",
    "Malachi": "מלאכי", "Psalms": "תהילים", "Proverbs": "משלי", "Job": "איוב", "Song of Songs": "שיר השירים", "Ruth": "רות",
    "Lamentations": "איכה", "Ecclesiastes": "קהלת", "Esther": "אסתר", "Daniel": "דניאל", "Ezra": "עזרא", "Nehemiah": "נחמיה",
    "I Chronicles": "דברי הימים א", "II Chronicles": "דברי הימים ב", "Torah": "תורה",
    # ---------------- tractates
    "Berakhot": "ברכות", "Peah": "פאה", "Demai": "דמאי", "Kilayim": "כלאים", "Sheviit": "שביעית", "Terumot": "תרומות",
    "Maasrot": "מעשרות", "Maaser Sheni": "מעשר שני", "Challah": "חלה", "Orlah": "ערלה", "Bikkurim": "ביכורים", "Shabbat": "שבת",
    "Eruvin": "עירובין", "Pesachim": "פסחים", "Shekalim": "שקלים", "Yoma": "יומא", "Sukkah": "סוכה", "Beitzah": "ביצה",
    "Rosh Hashanah": "ראש השנה", "Taanit": "תענית", "Megillah": "מגילה", "Moed Katan": "מועד קטן", "Chagigah": "חגיגה",
    "Yevamot": "יבמות", "Ketubot": "כתובות", "Nedarim": "נדרים", "Nazir": "נזיר", "Sotah": "סוטה", "Gittin": "גיטין",
    "Kiddushin": "קידושין", "Bava Kamma": "בבא קמא", "Bava Metzia": "בבא מציעא", "Bava Batra": "בבא בתרא", "Sanhedrin": "סנהדרין",
    "Makkot": "מכות", "Shevuot": "שבועות", "Eduyot": "עדיות", "Avodah Zarah": "עבודה זרה", "Pirkei Avot": "פרקי אבות",
    "Avot": "אבות", "Horayot": "הוריות", "Zevachim": "זבחים", "Menachot": "מנחות", "Chullin": "חולין", "Bekhorot": "בכורות",
    "Arakhin": "ערכין", "Temurah": "תמורה", "Keritot": "כריתות", "Meilah": "מעילה", "Tamid": "תמיד", "Middot": "מידות",
    "Kinnim": "קינים", "Kelim": "כלים", "Oholot": "אהלות", "Negaim": "נגעים", "Parah": "פרה", "Tahorot": "טהרות",
    "Mikvaot": "מקואות", "Niddah": "נדה", "Makhshirin": "מכשירין", "Zavim": "זבים", "Tevul Yom": "טבול יום", "Yadayim": "ידים",
    "Oktzin": "עוקצין", "Kelim Kamma": "כלים בבא קמא", "Kelim Metzia": "כלים בבא מציעא", "Kelim Batra": "כלים בבא בתרא",
    "Avot DeRabbi Natan": "אבות דרבי נתן", "Soferim": "סופרים", "Semachot": "שמחות", "Kallah": "כלה", "Derekh Eretz Rabbah": "דרך ארץ רבה",
    "Derekh Eretz Zuta": "דרך ארץ זוטא", "Gerim": "גרים", "Kutim": "כותים", "Avadim": "עבדים", "Sefer Torah": "ספר תורה",
    "Tefillin": "תפילין", "Tzitzit": "ציצית", "Mezuzah": "מזוזה",
    # ---------------- commentators & seforim (also used as categories)
    "Rashi": "רש״י", "Ramban": "רמב״ן", "Rambam": "רמב״ם", "Ibn Ezra": "אבן עזרא", "Sforno": "ספורנו", "Radak": "רד״ק",
    "Ralbag": "רלב״ג", "Rashbam": "רשב״ם", "Rashba": "רשב״א", "Ritva": "ריטב״א", "Ran": "ר״ן", "Rif": "רי״ף", "Rosh": "רא״ש",
    "Meiri": "מאירי", "Tosafot": "תוספות", "Tosafot Yom Tov": "תוספות יום טוב", "Ikar Tosafot Yom Tov": "עיקר תוספות יום טוב",
    "Bartenura": "ברטנורא", "Tiferet Yisrael": "תפארת ישראל", "Yachin": "יכין", "Boaz": "בועז", "Malbim": "מלבי״ם",
    "Malbim Beur Hamilot": "מלבי״ם ביאור המילות", "Or HaChaim": "אור החיים", "Kli Yakar": "כלי יקר", "Abarbanel": "אברבנאל",
    "Alshich": "אלשיך", "Chizkuni": "חזקוני", "Rabbeinu Bahya": "רבינו בחיי", "Rabbeinu Chananel": "רבינו חננאל",
    "Rabbeinu Gershom": "רבינו גרשום", "Rabbeinu Yonah": "רבינו יונה", "Ba'al HaTurim": "בעל הטורים", "Kitzur Ba'al HaTurim": "קיצור בעל הטורים",
    "Da'at Zekenim": "דעת זקנים", "Haamek Davar": "העמק דבר", "Harchev Davar": "הרחב דבר", "Siftei Chakhamim": "שפתי חכמים",
    "Gur Aryeh": "גור אריה", "Mizrachi": "מזרחי", "Torah Temimah": "תורה תמימה", "HaKtav VeHaKabalah": "הכתב והקבלה",
    "Shadal": "שד״ל", "Steinsaltz": "שטיינזלץ", "Metzudat David": "מצודת דוד", "Metzudat Zion": "מצודת ציון", "Minchat Shai": "מנחת שי",
    "Onkelos": "אונקלוס", "Targum Jonathan": "תרגום יונתן", "Targum Jerusalem": "תרגום ירושלמי", "Targum Neofiti": "תרגום ניאופיטי",
    "Saadia Gaon": "רס״ג", "Tafsir Rasag": "תפסיר רס״ג", "Bekhor Shor": "בכור שור", "Ralbag Beur HaMilot": "רלב״ג ביאור המילות",
    "Maharsha": "מהרש״א", "Maharshal": "מהרש״ל", "Maharam": "מהר״ם", "Maharam Schiff": "מהר״ם שיף", "Maharam of Padua": "מהר״ם פדואה",
    "Penei Yehoshua": "פני יהושע", "Rashash": "רש״ש", "Gilyon HaShas": "גליון הש״ס", "Mesorat HaShas": "מסורת הש״ס", "Ein Mishpat Ner Mitzvah": "עין משפט נר מצוה", "Torah Ohr": "תורה אור", "Hagahot HaBach": "הגהות הב״ח", "Hagahot HaGra": "הגהות הגר״א", "Tosafot Yom Tov": "תוספות יום טוב",
    "Shita Mekubetzet": "שיטה מקובצת", "Nimukei Yosef": "נמוקי יוסף", "Mordechai": "מרדכי", "Baal HaMaor": "בעל המאור",
    "Piskei Tosafot": "פסקי תוספות", "Tosafot HaRosh": "תוספות הרא״ש", "Tosafot Rid": "תוספות רי״ד", "Tosafot Yeshanim": "תוספות ישנים",
    "Tosafot Shantz": "תוספות שאנץ", "Tosafot Ri HaZaken": "תוספות רי״ד הזקן", "Tosafot Rabbi Akiva Eiger": "תוספות רבי עקיבא איגר",
    "Chiddushei Ramban": "חידושי הרמב״ן", "Chiddushei Rabbi Akiva Eiger": "חידושי רבי עקיבא איגר", "Rabbi Akiva Eiger": "רבי עקיבא איגר",
    "Chatam Sofer": "חתם סופר", "Chidushei Chatam Sofer": "חידושי חתם סופר", "Chidushei Agadot": "חידושי אגדות", "Chidushei Halachot": "חידושי הלכות",
    "Yad Ramah": "יד רמה", "Ri Migash": "רי מיגש", "Rav Nissim Gaon": "רב נסים גאון", "Shiltei HaGiborim": "שלטי הגבורים",
    "Ben Yehoyada": "בן יהוידע", "Benayahu": "בניהו", "Kessef Mishneh": "כסף משנה", "Maggid Mishneh": "מגיד משנה", "Lechem Mishneh": "לחם משנה",
    "Mishneh LaMelech": "משנה למלך", "Hasagot HaRa'avad": "השגות הראב״ד", "Migdal Oz": "מגדל עוז", "Radbaz": "רדב״ז", "Ohr Sameach": "אור שמח",
    "Kiryat Sefer": "קרית ספר", "Avodat HaMelekh": "עבודת המלך", "Sefer HaMitzvot": "ספר המצוות", "Turei Zahav": "טורי זהב", "Siftei Kohen": "שפתי כהן",
    "Magen Avraham": "מגן אברהם", "Mishnah Berurah": "משנה ברורה", "Ba'er Hetev": "באר היטב", "Be'er HaGolah": "באר הגולה",
    "Beur HaGra": "ביאור הגר״א", "Pri Megadim": "פרי מגדים", "Pitchei Teshuvah": "פתחי תשובה", "Ketzot HaChoshen": "קצות החושן",
    "Netivot HaMishpat, Beurim": "נתיבות המשפט, ביאורים", "Netivot HaMishpat, Hidushim": "נתיבות המשפט, חידושים", "Chelkat Mechokek": "חלקת מחוקק",
    "Beit Shmuel": "בית שמואל", "Me'irat Einayim": "מאירת עינים", "Kaf HaChayim": "כף החיים", "Chayei Adam": "חיי אדם",
    "Eliyah Rabbah": "אליה רבה", "Machatzit HaShekel": "מחצית השקל", "Peri Chadash": "פרי חדש", "Dagul MeRevava": "דגול מרבבה",
    "Nekudot HaKesef": "נקודות הכסף", "Chok Yaakov": "חק יעקב", "Urim VeTumim": "אורים ותומים", "Sha'arei Teshuvah": "שערי תשובה",
    "Gra": "הגר״א", "Chida": "חיד״א", "Maharal": "מהר״ל", "Ramchal": "רמח״ל", "Ramak": "רמ״ק", "Arizal and Chaim Vital": "האר״י ור׳ חיים ויטאל",
    "Baal HaSulam": "בעל הסולם", "Zohar": "זוהר", "Sefer Yetzirah": "ספר יצירה", "Rav Kook": "הרב קוק", "Chabad": "חב״ד",
    "Breslov": "ברסלב", "Izhbitz": "איזביצא", "Piaseczno Rebbe": "האדמו״ר מפיאסצנה", "R' Tzadok HaKohen": "ר׳ צדוק הכהן",
    "Duties of the Heart": "חובות הלבבות", "Guide for the Perplexed": "מורה נבוכים", "Milchemet Hashem": "מלחמות השם",
    "Matnot Kehunah": "מתנות כהונה", "Etz Yosef": "עץ יוסף", "Perush Maharzu": "פירוש מהרז״ו", "Maharzu Hakatzar": "מהרז״ו הקצר",
    "Yefeh To'ar": "יפה תואר", "Yefeh Anaf": "יפה ענף", "Midrash Lekach Tov": "מדרש לקח טוב", "Seder Olam Rabbah": "סדר עולם רבה",
    "Penei Moshe on Jerusalem Talmud": "פני משה על תלמוד ירושלמי", "Korban HaEdah on Jerusalem Talmud": "קרבן העדה על תלמוד ירושלמי",
    "Sheyarei Korban on Jerusalem Talmud": "שיירי קרבן על תלמוד ירושלמי", "Mareh HaPanim on Jerusalem Talmud": "מראה הפנים על תלמוד ירושלמי",
    "Melekhet Shelomoh": "מלאכת שלמה", "Rash MiShantz": "ר״ש משאנץ", "Tosefta Kifshutah": "תוספתא כפשוטה", "Masoret HaTosefta": "מסורת התוספתא",
    "Minchat Chinukh": "מנחת חינוך", "Sefer HaChinukh": "ספר החינוך", "Mishnat Eretz Yisrael": "משנת ארץ ישראל", "Peninei Halakhah": "פניני הלכה",
    "Jonathan Sacks": "הרב יונתן זקס", "Rabbi Lord Jonathan Sacks": "הרב יונתן זקס", "Covenant and Conversation": "שיג ושיח",
    "Redeeming Relevance": "רלוונטיות גואלת", "Eliezer Berkovits": "אליעזר ברקוביץ", "Aderet Eliyahu": "אדרת אליהו",
    "Rav Amiel": "הרב עמיאל", "Shem HaGedolim": "שם הגדולים", "Shoel uMeshiv": "שואל ומשיב", "Melammed Lehoil": "מלמד להועיל",
    "Meshech Hochma": "משך חכמה", "Tzafnat Pa'neach": "צפנת פענח", "Yam shel Shelomoh": "ים של שלמה", "Chokhmat Shlomo": "חכמת שלמה",
    "Sha'ar HaMelekh": "שער המלך", "Teshuvah MeYirah": "תשובה מיראה", "Imrei Yosher": "אמרי יושר", "Even Ha'azel": "אבן האזל",
    "Kovetz Al Yad HaChazakah": "קובץ על יד החזקה", "Mekorei HaRambam LeRashash": "מקורי הרמב״ם לרש״ש", "Yad Eitan": "יד איתן",
    "Mishnat DeRabbi Eliezer": "משנת דרבי אליעזר", "Tumat Yesharim": "תומת ישרים", "Lev Hakhamim": "לב חכמים", "Ben Aryeh": "בן אריה",
    "Chiddushei HaRim": "חידושי הרי״ם", "Gevurat Ari": "גבורת ארי", "Korban Netanel": "קרבן נתנאל", "Maadaney Yom Tov": "מעדני יום טוב",
    "Divrey Chamudot": "דברי חמודות", "Pilpula Charifta": "פלפולא חריפתא", "Tiferet Shmuel": "תפארת שמואל", "Hon Ashir": "הון עשיר",
    "Yesh Seder LaMishnah": "יש סדר למשנה", "Chidushei HaRadal": "חידושי הרד״ל", "Chiddushei Anshei Shem": "חידושי אנשי שם",
    "Chiddushei HaRa'ah": "חידושי הרא״ה", "Yad David": "יד דוד", "Yad Ephraim": "יד אפרים", "Hagahot HaBach": "הגהות הב״ח",
    "Hagahot Chavot Yair": "הגהות חוות יאיר", "Haggahot Ya'avetz": "הגהות יעב״ץ", "Haggahot R' Yeshaya Berlin": "הגהות ר׳ ישעיה ברלין",
    "Annotations of R' Yeshaya Berlin": "הגהות ר׳ ישעיה ברלין", "Annotations of Maharatz Chajes": "הגהות מהר״ץ חיות",
    "Annotations of Minchat Chinukh": "הערות מנחת חינוך", "Annotations of R' Zalman of Vilna": "הגהות ר׳ זלמן מווילנא",
    "Chomat Anakh": "חומת אנך", "Birkat Avraham": "ברכת אברהם", "Avi Ezer": "אבי עזר", "Ateret Zekenim": "עטרת זקנים",
    "Be'er Mayim Chaim": "באר מים חיים", "Be'er Sheva": "באר שבע", "Bedek HaBayit": "בדק הבית", "Mishmeret HaBayit": "משמרת הבית",
    "Benei Ahuvah": "בני אהובה", "Benei Binyamin": "בני בנימין", "Binah LeIttim": "בינה לעתים", "Binyan Yehoshua": "בנין יהושע",
    "Chemdat Yisrael": "חמדת ישראל", "Cheshek Shlomo": "חשק שלמה", "Chiddushei Hilkhot Niddah": "חידושי הלכות נדה",
    "Chidushei Mayim Chayim": "חידושי מים חיים", "Chidushim of Machaneh Ephraim": "חידושי מחנה אפרים", "Commentary of the Rosh": "פירוש הרא״ש",
    "Commentary of Chida": "פירוש החיד״א", "Divrei David": "דברי דוד", "Divrei Yirmiyahu": "דברי ירמיהו", "Eshel Avraham": "אשל אברהם",
    "Har HaMoriyah": "הר המוריה", "Katuv Sham": "כתוב שם", "Kereti": "כרתי", "Peleti": "פלתי", "Kisse Rahamim": "כסא רחמים",
    "Ktav Yad Rashi": "כתב יד רש״י", "Lechem Shamayim": "לחם שמים", "Lev Shalem": "לב שלם", "Levushei Serad": "לבושי שרד",
    "Ma'asai LaMelekh": "מעשה למלך", "Maaseh Rokeach": "מעשה רוקח", "Marit HaAyin": "מראית העין", "Mechokekei Yehudah": "מחוקקי יהודה",
    "Mitzpeh Etan": "מצפה איתן", "Nachal Eitan": "נחל איתן", "Nachal Eshkol": "נחל אשכול", "Nachalat Ya'akov": "נחלת יעקב",
    "Noam Yerushalmi": "נועם ירושלמי", "Petach Einayim": "פתח עינים", "Reshimot Shiurim": "רשימות שיעורים", "Rishon Letzion": "ראשון לציון",
    "Sefer HaMenucha": "ספר המנוחה", "Sefer HaZekhut": "ספר הזכות", "Sha'arei Torat Bavel": "שערי תורת בבל",
    "Sha'arei Torat Eretz Yisrael": "שערי תורת ארץ ישראל", "Shorshei HaYam": "שורשי הים", "Torat HaShlamim": "תורת השלמים",
    "Tur HaAroch": "הטור הארוך", "Tziunei Maharan": "ציוני מהר״ן", "Tziyyun LeNefesh Chayyah": "ציון לנפש חיה", "Yedei Moshe": "ידי משה",
    "Yefeh Kol": "יפה קול", "Yekar Tiferet": "יקר תפארת", "Yekhahen Pe'er": "יכהן פאר", "Yitzchak Yeranen": "יצחק ירנן",
    "Immanuel of Rome": "עמנואל הרומי", "Joseph ibn Yahya": "יוסף אבן יחייא", "Avraham Remer": "אברהם רמר", "Avodat HaKodesh (Chida)": "עבודת הקודש (חיד״א)",
    "B'Mareh HaBazak": "במראה הבזק", "Divrei Shaul Edut BeYosef": "דברי שאול עדות ביוסף", "Commentary of Mahari Kurkus and Radbaz": "פירוש מהר״י קורקוס ורדב״ז",
    "Commentary on Sefer Hamitzvot of Rasag": "פירוש על ספר המצוות לרס״ג", "Hagahot MeAlfas Yashan": "הגהות מאלפס ישן", "Hagahot Imrei Barukh": "הגהות אמרי ברוך",
    "Haggahot Kevod Melakhim": "הגהות כבוד מלכים", "Ha'atakat Teshuvat HaRif": "העתקת תשובת הרי״ף", "Amudei Yerushalayim on Jerusalem Talmud": "עמודי ירושלים על תלמוד ירושלמי",
    # ---------------- more commentators / works
    "Chiddushei Ridbaz": "חידושי רידב״ז", "Chidushei Rabbi Eliyahu of Greiditz": "חידושי רבי אליהו מגריידיץ", "Haggahot RaDO": "הגהות רד״א",
    "Haggahot Rabbi Menachem di Lonzano": "הגהות רבי מנחם די לונזאנו", "Haggahot YaFeM": "הגהות יפ״מ", "Kikar LaAden": "כיכר לעדן",
    "Ohr LaYesharim": "אור לישרים", "Sirilio": "ר״ש סיריליו", "Tosafot HaRid": "תוספות הרי״ד", "Amudei Yerushalayim": "עמודי ירושלים",
    "Penei Moshe": "פני משה", "Korban HaEdah": "קרבן העדה", "Sheyarei Korban": "שיירי קרבן", "Mareh HaPanim": "מראה הפנים",
    "Rif": "רי״ף", "HaMaor HaKatan": "המאור הקטן", "HaMaor HaGadol": "המאור הגדול", "Milchamot HaShem": "מלחמות ה׳", "Baba Batra": "בבא בתרא",
    "Baba Kamma": "בבא קמא", "Baba Metzia": "בבא מציעא", "Tze'enah Ure'enah": "צאנה וראנה", "Menorat HaMaor": "מנורת המאור",
    "Ohr Zarua": "אור זרוע", "Peri Tzadik": "פרי צדיק", "Tiferet Shlomo": "תפארת שלמה", "Torat HaAdam": "תורת האדם", "Ohr Yisrael": "אור ישראל",
    "Kol Dodi Dofek": "קול דודי דופק", "Talmud Eser HaSefirot": "תלמוד עשר הספירות", "Likutei Tefilot": "ליקוטי תפילות", "Shalom Aleichem": "שלום עליכם",
    "Tzror HaMor": "צרור המור", "Matteh Dan": "מטה דן", "Binyan Tziyon": "בנין ציון", "Noda BiYehudah I": "נודע ביהודה קמא",
    "Noda BiYehudah II": "נודע ביהודה תנינא", "Tur HaArokh": "הטור הארוך", "Mikdash Melekh": "מקדש מלך", "Zevach Pesach": "זבח פסח",
    "Devarim Tovim": "דברים טובים", "Marot HaTzoveot": "מראות הצובאות", "Piskei Challah": "פסקי חלה", "Adam Min HaAdamah": "אדם מן האדמה",
    "Irin Kadishin Tlita'a": "עירין קדישין תליתאה", "Tzav VeZeruz": "צו וזירוז", "Haggahot of Radal": "הגהות הרד״ל", "Sefer HaParnas": "ספר הפרנס",
    "Aramaic Targum to": "תרגום ארמי ל", "Edot HaMizrach": "עדות המזרח", "Sefard": "ספרד", "Ashkenaz": "אשכנז", "Mahzor": "מחזור",
    "Transmission of the Oral Law": "סדר מסירת תורה שבעל פה", "Tractate Tzitzit": "מסכת ציצית", "Pesach Haggadah": "הגדה של פסח",
    "Shir HaShirim Rabbah": "שיר השירים רבה", "Kohelet Rabbah": "קהלת רבה", "Eichah Rabbah": "איכה רבה", "Rabbi Sacks": "הרב זקס",
    "Yom Kippur": "יום כיפור", "Rosh Hashanah Mahzor": "מחזור ראש השנה", "Yom Kippur Mahzor": "מחזור יום כיפור", "Pesach": "פסח",
    "Shavuot": "שבועות", "Sukkot": "סוכות", "Tisha B'Av": "תשעה באב", "Teshuvot HaGeonim": "תשובות הגאונים", "Teshuvot HaRadbaz": "תשובות הרדב״ז",
    # ---------------- common stand-alone works
    "Mishneh Torah": "משנה תורה", "Kuzari": "כוזרי", "Mesillat Yesharim": "מסילת ישרים", "Orchot Tzadikim": "ארחות צדיקים",
    "Tanya": "תניא", "Likutei Moharan": "ליקוטי מוהר״ן", "Kitzur Shulchan Arukh": "קיצור שולחן ערוך", "Arukh HaShulchan": "ערוך השולחן",
    "Sefer HaChinukh": "ספר החינוך", "Shemoneh Perakim": "שמונה פרקים", "Derekh Hashem": "דרך השם", "Nefesh HaChayim": "נפש החיים",
    "Shulchan Arukh, Orach Chayim": "שולחן ערוך, אורח חיים", "Shulchan Arukh, Yoreh De'ah": "שולחן ערוך, יורה דעה",
    "Shulchan Arukh, Even HaEzer": "שולחן ערוך, אבן העזר", "Shulchan Arukh, Choshen Mishpat": "שולחן ערוך, חושן משפט",
    "Bereshit Rabbah": "בראשית רבה", "Shemot Rabbah": "שמות רבה", "Vayikra Rabbah": "ויקרא רבה", "Bamidbar Rabbah": "במדבר רבה",
    "Devarim Rabbah": "דברים רבה", "Shir HaShirim Rabbah": "שיר השירים רבה", "Ruth Rabbah": "רות רבה", "Eichah Rabbah": "איכה רבה",
    "Kohelet Rabbah": "קהלת רבה", "Esther Rabbah": "אסתר רבה", "Mekhilta d'Rabbi Yishmael": "מכילתא דרבי ישמעאל", "Sifra": "ספרא",
    "Sifrei Bamidbar": "ספרי במדבר", "Sifrei Devarim": "ספרי דברים", "Tanchuma": "תנחומא", "Midrash Tanchuma": "מדרש תנחומא",
    "Pirkei DeRabbi Eliezer": "פרקי דרבי אליעזר", "Yalkut Shimoni on Torah": "ילקוט שמעוני על התורה", "Midrash Tehillim": "מדרש תהילים",
    "Pesikta DeRav Kahanna": "פסיקתא דרב כהנא", "Tanna Debei Eliyahu Rabbah": "תנא דבי אליהו רבה", "Pesach Haggadah": "הגדה של פסח",
    "Siddur Ashkenaz": "סידור אשכנז", "Siddur Sefard": "סידור ספרד", "Siddur Edot HaMizrach": "סידור עדות המזרח",
    "Machzor Rosh Hashanah Ashkenaz": "מחזור ראש השנה אשכנז", "Machzor Yom Kippur Ashkenaz": "מחזור יום כיפור אשכנז",
    "Zohar": "זוהר", "Tikkunei Zohar": "תיקוני זוהר", "Etz Chaim": "עץ חיים", "Pardes Rimonim": "פרדס רימונים", "Tomer Devorah": "תומר דבורה",
    "Sefat Emet": "שפת אמת", "Kedushat Levi": "קדושת לוי", "Noam Elimelech": "נועם אלימלך", "Me'or Einayim": "מאור עינים",
    "Degel Machaneh Ephraim": "דגל מחנה אפרים", "Toldot Yaakov Yosef": "תולדות יעקב יוסף", "Mei HaShiloach": "מי השילוח",
    "Kedushat HaShabbat": "קדושת השבת", "Netivot Olam": "נתיבות עולם", "Orot": "אורות", "Orot HaKodesh": "אורות הקודש",
    "Iggeret HaKodesh": "אגרת הקודש", "Shaarei Teshuvah": "שערי תשובה", "Chofetz Chaim": "חפץ חיים", "Shemirat HaLashon": "שמירת הלשון",
    "Ahavat Chesed": "אהבת חסד", "Igrot Moshe": "אגרות משה", "Teshuvot HaRashba": "תשובות הרשב״א", "Teshuvot HaRosh": "תשובות הרא״ש",
    "Teshuvot Maharam": "תשובות מהר״ם", "Chatam Sofer on Torah": "חתם סופר על התורה", "Mishnah Berurah": "משנה ברורה",
    "Shulchan Arukh HaRav": "שולחן ערוך הרב", "Kaf HaChayim on Shulchan Arukh, Orach Chayim": "כף החיים על שולחן ערוך, אורח חיים",
    "Jerusalem Talmud": "תלמוד ירושלמי", "Book of Jubilees": "ספר היובלים", "Ben Sira": "בן סירא", "The Book of Maccabees I": "ספר מקבים א",
    "The Book of Maccabees II": "ספר מקבים ב", "Judith": "יהודית", "Tobit": "טוביה",
}
WORDS = {  # word-level fallbacks used inside composed names
    "Laws of": "הלכות", "Hilchot": "הלכות", "Hilkhot": "הלכות", "Introduction to": "הקדמה ל", "Commentary on": "פירוש על",
    "Notes on": "הערות על", "Rabbi": "רבי", "Rav": "רב", "Rabbeinu": "רבינו", "Sefer": "ספר", "Teshuvot": "תשובות", "Responsa": "שו״ת",
    "Chiddushei": "חידושי", "Chidushei": "חידושי", "Hagahot": "הגהות", "Haggahot": "הגהות", "Beur": "ביאור", "Perush": "פירוש",
    "Kitzur": "קיצור", "Likutei": "ליקוטי", "Iggerot": "אגרות", "Igrot": "אגרות", "Derashot": "דרשות", "Shaar": "שער", "Sha'ar": "שער",
}
MISHNEH_TORAH_LAWS = {
    "Foundations of the Torah": "יסודי התורה", "Human Dispositions": "דעות", "Torah Study": "תלמוד תורה", "Foreign Worship and Customs of the Nations": "עבודה זרה וחוקות הגויים",
    "Repentance": "תשובה", "Reading the Shema": "קריאת שמע", "Prayer and the Priestly Blessing": "תפילה וברכת כהנים", "Tefillin, Mezuzah and the Torah Scroll": "תפילין ומזוזה וספר תורה",
    "Fringes": "ציצית", "Blessings": "ברכות", "Circumcision": "מילה", "Sabbath": "שבת", "Eruvin": "עירובין", "Rest on the Tenth of Tishrei": "שביתת עשור",
    "Rest on a Holiday": "שביתת יום טוב", "Leavened and Unleavened Bread": "חמץ ומצה", "Shofar, Sukkah and Lulav": "שופר וסוכה ולולב", "Sheqel Dues": "שקלים",
    "Sanctification of the New Month": "קידוש החודש", "Fasts": "תעניות", "Scroll of Esther and Hanukkah": "מגילה וחנוכה", "Marriage": "אישות", "Divorce": "גירושין",
    "Levirate Marriage and Release": "יבום וחליצה", "Virgin Maiden": "נערה בתולה", "Woman Suspected of Infidelity": "סוטה", "Forbidden Intercourse": "איסורי ביאה",
    "Forbidden Foods": "מאכלות אסורות", "Ritual Slaughter": "שחיטה", "Oaths": "שבועות", "Vows": "נדרים", "Nazariteship": "נזירות", "Appraisals and Devoted Property": "ערכין וחרמין",
    "Diverse Species": "כלאים", "Gifts to the Poor": "מתנות עניים", "Heave Offerings": "תרומות", "Tithes": "מעשר", "Second Tithes and Fourth Year's Fruit": "מעשר שני ונטע רבעי",
    "First Fruits and other Gifts to Priests Outside the Sanctuary": "ביכורים ושאר מתנות כהונה", "Sabbatical Year and the Jubilee": "שמיטה ויובל",
    "The Chosen Temple": "בית הבחירה", "Vessels of the Sanctuary and Those Who Serve Therein": "כלי המקדש והעובדים בו", "Admission into the Sanctuary": "ביאת המקדש",
    "Things Forbidden on the Altar": "איסורי המזבח", "Sacrificial Procedure": "מעשה הקרבנות", "Daily Offerings and Additional Offerings": "תמידין ומוספין",
    "Sacrifices Rendered Unfit": "פסולי המוקדשין", "Service on the Day of Atonement": "עבודת יום הכפורים", "Trespass": "מעילה", "Paschal Offering": "קרבן פסח",
    "Festival Offering": "חגיגה", "Firstlings": "בכורות", "Offerings for Unintentional Transgressions": "שגגות", "Offerings for Those with Incomplete Atonement": "מחוסרי כפרה",
    "Substitution": "תמורה", "Defilement by a Corpse": "טומאת מת", "Red Heifer": "פרה אדומה", "Defilement by Leprosy": "טומאת צרעת",
    "Those Who Defile Bed or Seat": "מטמאי משכב ומושב", "Other Sources of Defilement": "שאר אבות הטומאות", "Defilement of Foods": "טומאת אוכלים",
    "Vessels": "כלים", "Immersion Pools": "מקואות", "Damages to Property": "נזקי ממון", "Theft": "גניבה", "Robbery and Lost Property": "גזילה ואבידה",
    "One Who Injures a Person or Property": "חובל ומזיק", "Murderer and the Preservation of Life": "רוצח ושמירת נפש", "Sales": "מכירה",
    "Ownerless Property and Gifts": "זכייה ומתנה", "Neighbors": "שכנים", "Agents and Partners": "שלוחין ושותפין", "Slaves": "עבדים", "Hiring": "שכירות",
    "Borrowing and Deposit": "שאלה ופקדון", "Creditor and Debtor": "מלווה ולווה", "Plaintiff and Defendant": "טוען ונטען", "Inheritances": "נחלות",
    "The Sanhedrin and the Penalties within their Jurisdiction": "סנהדרין והעונשין המסורין להם", "Testimony": "עדות", "Rebels": "ממרים", "Mourning": "אבל",
    "Kings and Wars": "מלכים ומלחמות",
}
HE_TITLE_OVERRIDES = {}  # filled at runtime from downloaded schemas (exact Sefaria Hebrew titles)


def _clean(s):
    return s.strip()


def he_name(name, depth=0):
    """Best Hebrew for an English title. '' if nothing sensible can be built."""
    if not name or depth > 4:
        return ""
    if name in HE_TITLE_OVERRIDES:
        return HE_TITLE_OVERRIDES[name]
    if name in NAMES:
        return NAMES[name]
    # "X on Y"
    m = re.match(r"^(.*?) on (.+)$", name)
    if m:
        a, b = he_name(m.group(1), depth + 1), he_name(m.group(2), depth + 1)
        if a and b:
            return f"{a} על {b}"
    # "Mishneh Torah, Laws of …" / "Shulchan Arukh, X"
    m = re.match(r"^Mishneh Torah, (.+)$", name)
    if m and m.group(1) in MISHNEH_TORAH_LAWS:
        return "משנה תורה, הלכות " + MISHNEH_TORAH_LAWS[m.group(1)]
    m = re.match(r"^(.+?), (.+)$", name)
    if m:
        a, b = he_name(m.group(1), depth + 1), he_name(m.group(2), depth + 1)
        if a and b:
            return f"{a}, {b}"
    # prefixes
    for pre, hp in (("Mishnah ", "משנה "), ("Tractate ", "מסכת "), ("Seder ", "סדר "), ("Rabbi Sacks on ", "הרב זקס על "), ("Onkelos ", "אונקלוס "), ("Targum Jonathan on ", "תרגום יונתן על "), ("Targum ", "תרגום "), ("Jerusalem Talmud ", "תלמוד ירושלמי "), ("Tosefta ", "תוספתא "), ("Midrash ", "מדרש "),
                    ("Sefer ", "ספר "), ("Teshuvot ", "תשובות "), ("Responsa ", "שו״ת "), ("Siddur ", "סידור "), ("Machzor ", "מחזור "),
                    ("Commentary on ", "פירוש על "), ("Introduction to ", "הקדמה ל"), ("Notes on ", "הערות על "), ("Chiddushei ", "חידושי "),
                    ("Chidushei ", "חידושי "), ("Hagahot ", "הגהות "), ("Kitzur ", "קיצור "), ("Likutei ", "ליקוטי "), ("Beur ", "ביאור ")):
        if name.startswith(pre):
            rest = he_name(name[len(pre):], depth + 1)
            if rest:
                return hp + rest
    # "Tractate X", "Seder X (Y)", "... Volume N", "Aramaic Targum to X", "X Sefard"
    m = re.match(r"^(.*?) Volume (\d+)$", name)
    if m:
        a = he_name(m.group(1), depth + 1)
        if a:
            return f"{a} חלק {m.group(2)}"
    m = re.match(r"^Aramaic Targum to (.+)$", name)
    if m and he_name(m.group(1), depth + 1):
        return "תרגום ארמי ל" + he_name(m.group(1), depth + 1)
    m = re.match(r"^(.+?) (Ashkenaz|Sefard|Edot HaMizrach|I|II|III)$", name)
    if m:
        a = he_name(m.group(1), depth + 1)
        if a:
            return f"{a} " + {"I": "א", "II": "ב", "III": "ג"}.get(m.group(2), NAMES.get(m.group(2), ""))
    m = re.match(r"^Mussafia (.+)$", name) or re.match(r"^Musafia (.+)$", name)
    if m and he_name(m.group(1), depth + 1):
        return he_name(m.group(1), depth + 1) + " (מוסאפיה)"
    m = re.match(r"^(.+?)( on)? Jerusalem Talmud (.+)$", name)
    if m:
        a, b = he_name(m.group(1), depth + 1), he_name(m.group(3), depth + 1)
        if a and b:
            return f"{a} על תלמוד ירושלמי {b}"
    m = re.match(r"^(.+?) on Rif (.+)$", name)
    if m:
        a, b = he_name(m.group(1), depth + 1), he_name(m.group(2), depth + 1)
        if a and b:
            return f"{a} על רי״ף {b}"
    m = re.match(r"^Rif (.+)$", name)
    if m and he_name(m.group(1), depth + 1):
        return "רי״ף " + he_name(m.group(1), depth + 1)
    # "X Rabbah", "Tosefta X (Lieberman)"
    m = re.match(r"^(.*?) \((.*?)\)$", name)
    if m:
        a = he_name(m.group(1), depth + 1)
        if a:
            b = he_name(m.group(2), depth + 1)
            return f"{a} ({b})" if b else a
    return ""


def load_overrides(mapping):
    HE_TITLE_OVERRIDES.update({k: v for k, v in mapping.items() if k and v})
