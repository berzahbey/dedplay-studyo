"""Seslendirme karışma ölçüsü (19 Ekim 2026). Seslendirmeye giden metinde ana metin olmayan parçaları kitap kitap sayar.

Ölçülen metin: her kitabın Stüdyo parçaları (kutuphane.cikti.studyo_parcalari, yalnız Parca_: Kitap Okuma'ya giden metin),
kitap.json'dan o anki kodla üretilir. Yamalı kodla (/k) ve imajdaki kodla (/app) ayrı ayrı çalıştırılıp karşılaştırılır.
  olc <kitaplar klasörü> <sonuc.json> [ayrinti.txt]     ölçer, özeti ekrana yazar
  karsilastir <eski.json> <yeni.json>                  kitap kitap önce/sonra
Kitaplara dokunmaz (salt okur)."""
import collections, glob, json, os, re, sys

SURE = ("Fatiha|Fâtiha|Bakara|Âl-i İmrân|Âl-i İmran|Al-i İmran|Nisâ|Nisa|Mâide|Maide|En'âm|Enâm|Enam|A'râf|Araf|Enfâl|Enfal|Tevbe|Yûnus|Yunus|Hûd|Hud|"
        "Yusuf|Yûsuf|Ra'd|İbrâhîm|İbrahim|Hicr|Nahl|İsrâ|İsra|Kehf|Meryem|Tâhâ|Taha|Enbiyâ|Enbiya|Hac|Mü'minûn|Müminun|Nûr|Nur|Furkan|Furkân|Şuarâ|Şuara|"
        "Neml|Kasas|Ankebût|Ankebut|Rum|Rûm|Lokman|Lukmân|Secde|Ahzâb|Ahzab|Sebe'|Sebe|Fâtır|Fatır|Yâsin|Yasin|Sâffât|Saffat|Sâd|Zümer|Mü'min|Gâfir|Gafir|"
        "Fussilet|Şûrâ|Şura|Zuhruf|Duhân|Duhan|Câsiye|Casiye|Ahkâf|Ahkaf|Fetih|Hucurât|Hucurat|Zâriyât|Zariyat|Tûr|Necm|Kamer|Rahmân|Vâkıa|Vâkia|"
        "Vakıa|Hadîd|Hadid|Mücâdele|Mücadele|Haşr|Mümtehine|Saff|Cum'a|Cuma|Münâfikûn|Münafikun|Teğâbün|Tegabün|Talâk|Talak|Tahrîm|Tahrim|Mülk|Kalem|"
        "Hâkka|Hakka|Meâric|Nûh|Nuh|Müzzemmil|Müddessir|Kıyâme|Kıyame|İnsan|Mürselât|Nebe'|Nebe|Nâziât|Abese|Tekvîr|Tekvir|İnfitâr|Mutaffifîn|"
        "İnşikâk|Bürûc|Büruc|Târık|A'lâ|Ğâşiye|Gaşiye|Fecr|Beled|Şems|Leyl|Duhâ|İnşirâh|Tîn|Alak|Kadr|Beyyine|Zilzâl|Âdiyât|Kâria|Tekâsür|Tekasür|Asr|"
        "Hümeze|Fîl|Kureyş|Mâûn|Maun|Kevser|Kâfirûn|Nasr|Tebbet|İhlâs|Felak|Nâs")
HADIS = r"Buhârî|Buhari|Müslim|Tirmizî|Tirmizi|Ebû Dâvûd|Ebu Davud|Nesâî|Nesai|İbn Mâce|İbn Mace|Müsned|Dârimî|Darimi|Muvatta|Beyhakî|Taberânî|Hâkim"
SEHIR = r"Paris|London|Londra|Leiden|Leyden|Kahire|Cairo|Beyrut|Beirut|Berlin|Oxford|Cambridge|Roma|Rome|Cezayir|Alger|Tunus|Bombay|Kalküta|Calcutta|Lahor|Lahore|Leipzig|Wiesbaden|New York|Princeton|Chicago|İstanbul|Ankara|Bağdat|Bağdad|Dımaşk|Şam|Haydarabad|Delhi|Tahran|Bulak|Bûlâk|Madrid|Napoli|Wien|Viyana|Göttingen|Tübingen|Hamburg|Torino"
D = [
    ("kaynakca_satiri", re.compile(rf"(?:\b(?:{SEHIR})\b[^.\n]{{0,40}}\b1[5-9]\d\d\b|\b(?:Yay\.|Yayınları|baskı|bsk\.|ed\.|trans\.|tr\.|vol\.|Vol\.|pp\.|Press|Verlag|éd\.|Bd\.)[^\n]{{0,60}}\b(?:1[5-9]|20)\d\d\b)"),
     "kaynakça girişi (şehir/yayınevi + yıl)"),
    ("sure_atfi", re.compile(rf"(?<!\w)(?:{SURE})\s*[,:/]\s*\d{{1,3}}(?:\s*[-–]\s*\d{{1,3}})?"), "âyet atfı (Bakara, 255)"),
    ("hadis_kaynagi", re.compile(rf"(?<!\w)(?:{HADIS})\s*,\s*[^\n,;]{{2,30}},\s*\d{{1,4}}"), "hadis kaynağı (Tirmizî, Zühd, 25)"),
    ("satir_ici_atif", re.compile(r"\((?:[A-ZÇĞİÖŞÜ]{1,3}\.|bkz\.?|bk\.|bak\.|a\.g\.e\.?|age\.?|s\.|sh\.|c\.)\s*\d{1,4}[^)]{0,20}\)|\ba\.g\.e\.|\ba\.g\.m\.|\bage\.,"),
     "satır içi atıf ((M. 54), (bkz. s. 12), a.g.e.)"),
    ("not_isareti", re.compile(r"<sup>|\[\d{1,3}\]|\(\*+\)|\{\{n\d+\}\}"), "dipnot işareti/kalıntısı"),
    ("noktalama", re.compile(r"(?:[.,;:]\s*){4,}|[,;:]\s*[,;:]|\(\s*\)|\s[-–—_]{2,}\s|\s[.,;:](?=\s+[a-zçğıöşü])"), "gereksiz noktalama"),
    ("cop", re.compile(r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF]|[^\w\s.,;:!?'\"\u2019\u2018\u201c\u201d\u00ab\u00bb()\[\]\-\u2013\u2014\u2026/%&+=*\u00a7\u00b0\u02bf\u02be`\u2022\u00b7\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]"),
     "tanınmayan işaret (OCR çöpü)"),
]
ANA_DISI = re.compile(r"^\s*(KAYNAKÇA|KAYNAKLAR|BİBLİYOGRAFYA|BIBLIYOGRAFYA|BIBLIOGRAPHY|DİZİN|INDEKS|İNDEKS|INDEX|SÖZLÜK|LÜGAT|TERİMLER|KISALTMALAR|"
                      r"YARARLANILAN|ANA KAYNAKLAR|TAHKİK|NOTLAR|İÇİNDEKİLER|ICINDEKILER|FİHRİST|KRONOLOJİ|ESER(?:LER)? HAKKINDA)\b", re.I)


YIL = re.compile(r"\b(?:1[5-9]\d\d|20\d\d)\b")
DIZIN = re.compile(r"^[^:.!?]{2,50}:\s*[^.!?]{0,60}?\b\d{1,3}(?:\s*(?:vd\.?|n\.\s*\d+))?(?:\s*[,;]\s*\d{1,3}(?:\s*(?:vd\.?|n\.\s*\d+))?)*\s*\.?$")


def _kucuk(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def kitap_metni(yol):
    sys.path.insert(0, os.environ.get("OLCU_KOD", "/app"))
    from kutuphane import kitap as K
    from kutuphane import cikti as C
    kit = K.yukle(yol)
    if "tr" not in K.diller(K.gorunur(kit)):
        return None, None
    ad = kit["kunye"]["baslik"].get("tr") or ""
    return ad, [p["tr"] for p in C.studyo_parcalari(kit) if p["name"].startswith("Parca_")]


def olc(ad, parcalar):
    metin = "\n".join(parcalar)
    kelime = len(metin.split())
    say, ornek = collections.Counter(), collections.defaultdict(list)
    def ekle(tur, bas, son, m=metin):
        say[tur] += 1
        if len(ornek[tur]) < 8:
            ornek[tur].append(m[max(0, bas - 70):son + 50].replace("\n", " / "))
    for tur, rx, _ in D:
        for m in rx.finditer(metin):
            ekle(tur, m.start(), m.end())
    # ana metin olmayan bölüm: başlığı kaynakça/dizin… ya da satırlarının çoğu kaynakça girişi / dizin satırı
    for p in parcalar:
        sat = [s for s in p.split("\n") if s.strip()]
        ilk = sat[0] if sat else ""
        yil = sum(1 for s in sat if YIL.search(s)) / max(1, len(sat))
        dizin = sum(1 for s in sat if DIZIN.match(s)) / max(1, len(sat))
        kisa = len(sat) * 1000 / max(1, len(p.split()))   # 1000 kelimede satır: düz metinde ~5-15, liste/kaynakça/dizinde 40+
        neden = ("başlık" if ANA_DISI.match(ilk) else "kaynakça" if len(sat) >= 10 and kisa >= 30 and yil >= 0.4 else
                 "dizin/sözlük" if len(sat) >= 10 and kisa >= 30 and dizin >= 0.4 else None)
        if neden:
            say["ana_disi_bolum_kelime"] += len(p.split())
            if len(ornek["ana_disi_bolum"]) < 12:
                ornek["ana_disi_bolum"].append(f"{neden}: {ilk[:60]} ({len(p.split())} kelime)")
    # kitap adı ve sayfa üst bilgisi: satırın başında değil, cümle içinde kitap adı ya da "Ad … 215 küçük harf"
    adk = [w for w in re.split(r"\W+", _kucuk(ad)) if len(w) >= 3][:3]
    if len(adk) >= 2:
        rx = re.compile(r"\b" + r"\W+".join(re.escape(w[:max(3, int(len(w) * 0.85))]) + r"\w{0,%d}" % (len(w) - max(3, int(len(w) * 0.85)) + 1) for w in adk) + r"\b", re.I)
        for p in parcalar:
            for s in p.split("\n")[1:]:
                for m in rx.finditer(_kucuk(s)):
                    if m.start() > 0 or (len(s.split()) <= 6 and not s.rstrip().endswith((".", ":", "!", "?"))):
                        ekle("kitap_adi", m.start(), m.end(), s)
    for m in re.finditer(r"(?<=[a-zçğıöşüâîû,]) (?:[A-ZÇĞİÖŞÜ][\w'’]+,? ){1,6}\d{1,3}(?= [a-zçğıöşüâîû\"“«(])", metin):
        ekle("ust_bilgi", m.start(), m.end())
    # üst bilgi satırı ("Helal rizik aramak 111") ya da bulanık kitap adıyla başlayan satır ("Dunle Kirk Prensip")
    import difflib
    adn = " ".join(adk)
    for p in parcalar:
        for s in p.split("\n")[1:]:
            k = s.split()
            if 2 <= len(k) <= 10 and s[:1].isupper() and re.search(r"[^\W\d]\s+\d{1,3}$", s) and not re.search(r"[.!?:;]", s):
                ekle("ust_bilgi", 0, len(s), s)
            elif len(adk) >= 2 and len(k) >= len(adk):
                bas = _kucuk(" ".join(k[:len(adk)]))
                if difflib.SequenceMatcher(None, bas, adn).ratio() >= 0.86 and not rx.search(_kucuk(s)):
                    ekle("kitap_adi", 0, len(s), s)
    return kelime, say, ornek


def ana():
    kip = sys.argv[1] if len(sys.argv) > 1 else ""
    if kip == "olc":
        kok, cikti = sys.argv[2], sys.argv[3]
        ayr = open(sys.argv[4], "w", encoding="utf-8") if len(sys.argv) > 4 else None
        sonuc = {}
        for yol in sorted(glob.glob(os.path.join(kok, "*", "kitap.json"))):
            kid = os.path.basename(os.path.dirname(yol))
            try:
                ad, parcalar = kitap_metni(yol)
            except Exception as e:
                print(f"{kid}: OKUNAMADI {type(e).__name__}: {e}")
                continue
            if parcalar is None:
                continue
            kelime, say, ornek = olc(ad, parcalar)
            toplam = sum(v for k, v in say.items() if not k.endswith("_kelime"))
            sonuc[kid] = {"ad": ad, "kelime": kelime, "say": dict(say), "toplam": toplam, "ornek": ornek}
            dis = say["ana_disi_bolum_kelime"]
            print(f"{kid[:42]:<42} {kelime:>7} kelime | karışma {toplam:>5} | ana metin dışı bölüm ~{dis} kelime | " +
                  ", ".join(f"{k}={v}" for k, v in sorted(say.items()) if v and not k.endswith("_kelime")))
            if ayr:
                ayr.write(f"\n######## {kid} — {ad} ({kelime} kelime)\n")
                for tur, ls in ornek.items():
                    for o in ls:
                        ayr.write(f"  [{tur}] …{o}…\n")
        json.dump(sonuc, open(cikti, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"TOPLAM {len(sonuc)} kitap, karışma {sum(v['toplam'] for v in sonuc.values())}")
    elif kip == "karsilastir":
        e, y = (json.load(open(f, encoding="utf-8")) for f in sys.argv[2:4])
        for kid in sorted(set(e) | set(y)):
            a, b = e.get(kid, {}), y.get(kid, {})
            turler = sorted(set(a.get("say", {})) | set(b.get("say", {})))
            fark = [f"{t} {a.get('say', {}).get(t, 0)}→{b.get('say', {}).get(t, 0)}" for t in turler
                    if a.get("say", {}).get(t, 0) != b.get("say", {}).get(t, 0)]
            print(f"{kid[:42]:<42} kelime {a.get('kelime', 0)}→{b.get('kelime', 0)} | " + ("; ".join(fark) or "AYNI"))
    else:
        print(__doc__)


if __name__ == "__main__":
    ana()
