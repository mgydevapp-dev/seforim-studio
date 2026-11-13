"""Speed / quality check of offline Hebrew->English translators (OPUS-MT, University of Helsinki) with CTranslate2."""
import sys, time, ctranslate2, transformers
SAMPLES = [
 "משנה. מאימתי קורין את שמע בערבית. משעה שהכהנים נכנסים לאכול בתרומתן, עד סוף האשמורה הראשונה, דברי רבי אליעזר. וחכמים אומרים, עד חצות.",
 "גמרא. תנא היכא קאי דקתני מאימתי ותו מאי שנא דתני בערבית ברישא לתני דשחרית ברישא תנא אקרא קאי דכתיב בשכבך ובקומך",
 "בראשית ברא אלהים את השמים ואת הארץ.",
 "מאימתי קורין את שמע בערבית - משעה שהכהנים נכנסים לאכול בתרומתן, כהנים שנטמאו וטבלו והעריב שמשן והגיע זמנן לאכול בתרומה.",
 "אדם מתעטף בטלית ומברך להתעטף בציצית, ואם היה לבוש בה מערב יום טוב צריך לברך עליה בבוקר.",
 "ואמר רבי יוחנן משום רבי שמעון בן יוחי כל העוסק בתורה בלילה שכינה כנגדו.",
]
for name in sys.argv[1:]:
    d = "ct2_" + name.split("/")[-1]
    tok = transformers.AutoTokenizer.from_pretrained(name)
    tr = ctranslate2.Translator(d, device="cpu", compute_type="int8", inter_threads=1, intra_threads=4)
    batch = SAMPLES * 20
    t0 = time.time()
    src = [tok.convert_ids_to_tokens(tok.encode(s)) for s in batch]
    out = tr.translate_batch(src, max_batch_size=32, beam_size=2)
    dt = time.time() - t0
    words = sum(len(s.split()) for s in batch)
    print(f"== {name}: {words / dt:.0f} Hebrew words/s")
    for s, o in zip(SAMPLES, out[:len(SAMPLES)]):
        print(" ", tok.decode(tok.convert_tokens_to_ids(o.hypotheses[0]), skip_special_tokens=True))
