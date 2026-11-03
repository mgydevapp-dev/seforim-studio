"""Create a small Sefaria-format sample (same layout as the real export) for testing offline.
Writes into <data>/sefaria/json/... and <data>/sefaria/links/links_sample.csv"""
import json
import os
import sys

GEN_HE = [[
    "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ׃",
    "וְהָאָ֗רֶץ הָיְתָ֥ה תֹ֙הוּ֙ וָבֹ֔הוּ וְחֹ֖שֶׁךְ עַל־פְּנֵ֣י תְה֑וֹם וְר֣וּחַ אֱלֹהִ֔ים מְרַחֶ֖פֶת עַל־פְּנֵ֥י הַמָּֽיִם׃",
    "וַיֹּ֥אמֶר אֱלֹהִ֖ים יְהִ֣י א֑וֹר וַֽיְהִי־אֽוֹר׃",
    "וַיַּ֧רְא אֱלֹהִ֛ים אֶת־הָא֖וֹר כִּי־ט֑וֹב וַיַּבְדֵּ֣ל אֱלֹהִ֔ים בֵּ֥ין הָא֖וֹר וּבֵ֥ין הַחֹֽשֶׁךְ׃",
    "וַיִּקְרָ֨א אֱלֹהִ֤ים ׀ לָאוֹר֙ י֔וֹם וְלַחֹ֖שֶׁךְ קָ֣רָא לָ֑יְלָה וַֽיְהִי־עֶ֥רֶב וַֽיְהִי־בֹ֖קֶר י֥וֹם אֶחָֽד׃ {פ}",
], [
    "וַיְכֻלּ֛וּ הַשָּׁמַ֥יִם וְהָאָ֖רֶץ וְכׇל־צְבָאָֽם׃",
    "וַיְכַ֤ל אֱלֹהִים֙ בַּיּ֣וֹם הַשְּׁבִיעִ֔י מְלַאכְתּ֖וֹ אֲשֶׁ֣ר עָשָׂ֑ה וַיִּשְׁבֹּת֙ בַּיּ֣וֹם הַשְּׁבִיעִ֔י מִכׇּל־מְלַאכְתּ֖וֹ אֲשֶׁ֥ר עָשָֽׂה׃",
    "וַיְבָ֤רֶךְ אֱלֹהִים֙ אֶת־י֣וֹם הַשְּׁבִיעִ֔י וַיְקַדֵּ֖שׁ אֹת֑וֹ כִּ֣י ב֤וֹ שָׁבַת֙ מִכׇּל־מְלַאכְתּ֔וֹ אֲשֶׁר־בָּרָ֥א אֱלֹהִ֖ים לַעֲשֽׂוֹת׃ {פ}",
]]
GEN_EN = [[
    "In the beginning God created the heaven and the earth.",
    "Now the earth was unformed and void, and darkness was upon the face of the deep; and the spirit of God hovered over the face of the waters.",
    "And God said: 'Let there be light.' And there was light.",
    "And God saw the light, that it was good; and God divided the light from the darkness.",
    "And God called the light Day, and the darkness He called Night. And there was evening and there was morning, one day.",
], [
    "And the heaven and the earth were finished, and all the host of them.",
    "And on the seventh day God finished His work which He had made; and He rested on the seventh day from all His work which He had made.",
    "And God blessed the seventh day, and hallowed it; because that in it He rested from all His work which God in creating had made.",
]]
BER_HE = [[], [], [
    "<b>מֵאֵימָתַי</b> קוֹרִין אֶת שְׁמַע בְּעַרְבִית? מִשָּׁעָה שֶׁהַכֹּהֲנִים נִכְנָסִים לֶאֱכוֹל בִּתְרוּמָתָן, עַד סוֹף הָאַשְׁמוּרָה הָרִאשׁוֹנָה, דִּבְרֵי רַבִּי אֱלִיעֶזֶר.",
    "וַחֲכָמִים אוֹמְרִים: עַד חֲצוֹת. רַבָּן גַּמְלִיאֵל אוֹמֵר: עַד שֶׁיַּעֲלֶה עַמּוּד הַשַּׁחַר.",
], [
    "תָּנָא קָאֵי הֵיכָא דְּקָתָנֵי מֵאֵימָתַי, וְתוּ מַאי שְׁנָא דְּתָנֵי בְּעַרְבִית בְּרֵישָׁא.",
]]
BER_EN = [[], [], [
    "<b>MISHNA:</b> From when does one recite <i>Shema</i> in the evening? From the time when the priests enter to partake of their teruma.",
    "And the Rabbis say: Until midnight. Rabban Gamliel says: Until the dawn breaks.",
], [
    "GEMARA: On what basis does the tanna of our mishna stand that he teaches: From when?",
]]
RASHI_HE = [[["בראשית ברא. אָמַר רַבִּי יִצְחָק לֹא הָיָה צָרִיךְ לְהַתְחִיל אֶת הַתּוֹרָה אֶלָּא מֵהַחֹדֶשׁ הַזֶּה לָכֶם",
              "בראשית ברא. אֵין הַמִּקְרָא הַזֶּה אוֹמֵר אֶלָּא דָּרְשֵׁנִי"], ["תהו ובהו. תֹּהוּ לְשׁוֹן תֵּמַהּ וְשִׁמָּמוֹן"]]]
RASHI_EN = [[["IN THE BEGINNING — Rabbi Isaac said: The Torah should have commenced with the verse This month shall be unto you."], []]]
AVOT_HE = {"Introduction": ["הקדמה לפרקי אבות, משה קיבל תורה מסיני"],
           "": [["מֹשֶׁה קִבֵּל תּוֹרָה מִסִּינַי, וּמְסָרָהּ לִיהוֹשֻׁעַ", "שִׁמְעוֹן הַצַּדִּיק הָיָה מִשְּׁיָרֵי כְנֶסֶת הַגְּדוֹלָה"]]}


def write(base, cat_path, title, lang, text, he_title, section_names, schema=None):
    d = os.path.join(base, "json", *cat_path.split(" > "), title, lang)
    os.makedirs(d, exist_ok=True)
    js = {"title": title, "heTitle": he_title, "language": "he" if lang == "Hebrew" else "en",
          "versionTitle": "merged", "sectionNames": section_names, "text": text,
          "schema": schema or {"sectionNames": section_names, "addressTypes": ["Talmud", "Integer"] if section_names[0] == "Daf" else ["Integer"] * len(section_names)}}
    with open(os.path.join(d, "merged.json"), "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False)


def main(data_dir):
    base = os.path.join(data_dir, "sefaria")
    write(base, "Tanakh > Torah", "Genesis", "Hebrew", GEN_HE, "בראשית", ["Chapter", "Verse"])
    write(base, "Tanakh > Torah", "Genesis", "English", GEN_EN, "בראשית", ["Chapter", "Verse"])
    write(base, "Talmud > Bavli > Seder Zeraim", "Berakhot", "Hebrew", BER_HE, "ברכות", ["Daf", "Line"])
    write(base, "Talmud > Bavli > Seder Zeraim", "Berakhot", "English", BER_EN, "ברכות", ["Daf", "Line"])
    write(base, "Tanakh > Rishonim on Tanakh > Rashi > Torah", "Rashi on Genesis", "Hebrew", RASHI_HE, "רש״י על בראשית",
          ["Chapter", "Verse", "Comment"])
    write(base, "Tanakh > Rishonim on Tanakh > Rashi > Torah", "Rashi on Genesis", "English", RASHI_EN, "רש״י על בראשית",
          ["Chapter", "Verse", "Comment"])
    schema = {"nodes": [{"title": "Introduction", "sectionNames": ["Paragraph"], "addressTypes": ["Integer"]},
                        {"title": "", "default": True, "sectionNames": ["Chapter", "Mishnah"], "addressTypes": ["Integer", "Integer"]}]}
    write(base, "Mishnah > Seder Nezikin", "Pirkei Avot", "Hebrew", AVOT_HE, "פרקי אבות", ["Chapter", "Mishnah"], schema)
    os.makedirs(os.path.join(base, "links"), exist_ok=True)
    with open(os.path.join(base, "links", "links_sample.csv"), "w", encoding="utf-8") as f:
        f.write('Citation 1,Citation 2,Conection Type,Text 1,Text 2,Category 1,Category 2\n')
        f.write('Genesis 1:1,Rashi on Genesis 1:1:1,commentary,Genesis,Rashi on Genesis,Tanakh,Commentary\n')
        f.write('Genesis 1:1,Rashi on Genesis 1:1:2,commentary,Genesis,Rashi on Genesis,Tanakh,Commentary\n')
        f.write('Genesis 1:2,Rashi on Genesis 1:2:1,commentary,Genesis,Rashi on Genesis,Tanakh,Commentary\n')
        f.write('Genesis 2:1-3,Berakhot 2a:1,reference,Genesis,Berakhot,Tanakh,Talmud\n')
        f.write('Genesis 1:5,Berakhot 2a:1,reference,Genesis,Berakhot,Tanakh,Talmud\n')
    schemas = os.path.join(base, "schemas")
    os.makedirs(schemas, exist_ok=True)
    with open(os.path.join(schemas, "Rashi_on_Genesis.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Rashi on Genesis", "heTitle": "רש״י על בראשית", "authors": [{"en": "Rashi", "he": "רש״י"}],
                   "compDate": [1075, 1105], "era": "RI", "compPlace": "Troyes", "enDesc": "Rashi's commentary on Genesis."}, f)
    print("sample written to", base)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "data"))
