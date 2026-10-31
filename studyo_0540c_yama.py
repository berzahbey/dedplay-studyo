# Studyo 0.5.40c: acilmis ara sozun kapanis cizgisi parca kisa olsa da kalir (degil- acz, olmasa da- alemin, ise- hummali)
# Kod klasorunde calistirilir. Tekrar calistirilabilir: yapilmis degisiklik ATLANDI der; beklenen metin yoksa HATA ile durur.
import sys, os

def oku(y):
    return open(y, encoding="utf-8").read()

def degistir(yol, eski, yeni):
    s = oku(yol)
    if s.count(yeni) == 1 and s.count(eski) == 0:
        print("ATLANDI:", yol, repr(yeni[:60]))
        return
    if s.count(eski) != 1:
        print("HATA:", yol, "beklenen metin", s.count(eski), "kez bulundu:", repr(eski[:80]))
        sys.exit(1)
    open(yol, "w", encoding="utf-8").write(s.replace(eski, yeni))
    print("TAMAM:", yol, repr(yeni[:60]))

def dosya(yol, icerik):
    if os.path.exists(yol) and oku(yol) == icerik:
        print("ATLANDI:", yol)
        return
    open(yol, "w", encoding="utf-8").write(icerik)
    print("TAMAM:", yol)

degistir('app/textsrc.py',
    '    try:\n        from app import duzelt as _dz\n        if len(sol) > 3 and len(sag) > 3 and not _dz._gecerli_kelime(sol + sag) and _dz._gecerli_kelime(sol) \\\n                and _dz._gecerli_kelime(sag):\n',
    '    try:\n        from app import duzelt as _dz\n        if not _dz._gecerli_kelime(sol + sag) and _dz.acik_ara_soz(m.string, m.start(1)):\n            return sol + "- " + sag      # 0.5.40c: açılmış ara sözün kapanış çizgisi (olmasa da- âlemin)\n        if len(sol) > 3 and len(sag) > 3 and not _dz._gecerli_kelime(sol + sag) and _dz._gecerli_kelime(sol) \\\n                and _dz._gecerli_kelime(sag):\n')
degistir('app/duzelt.py',
    '_SATIR_ICI_TIRE = re.compile(r"(?<![\\w-])([^\\W\\d_]{2,})-([a-zçğıöşüâîû]{2,})(?![\\w-])")\n\n\ndef satir_ici_tireleri_birlestir(p):\n    """EPUB\'da satır içinde kalmış heceleme tiresi: Merini-ler -> Meriniler (sağ parça tek başına kelime değilse).\n    İzafet (Kur\'an-ı) ve gerçek birleşik yazımlara (Âl-i) dokunulmaz."""\n',
    '_SATIR_ICI_TIRE = re.compile(r"(?<![\\w-])([^\\W\\d_]{2,})-([a-zçğıöşüâîû]{2,})(?![\\w-])")\n\n\n_ACILIS_CIZGI = re.compile(r"(?:^|[\\s(])[-–—](?=[^\\W\\d_])")\n_KAPANIS_CIZGI = re.compile(r"[^\\W\\d_][-–—](?:\\s|$)")\n\n\ndef acik_ara_soz(metin, bas):\n    """0.5.40c: bas\'tan önceki 250 harfte açılmış, henüz kapanmamış ara söz çizgisi var mı ("-dilsizlik değil- acz", "–tâbir caiz ise- hummalı")?"""\n    once = metin[max(0, bas - 250):bas]\n    acik = [m.end() for m in _ACILIS_CIZGI.finditer(once)]\n    return bool(acik) and not _KAPANIS_CIZGI.search(once[acik[-1]:])\n\n\ndef satir_ici_tireleri_birlestir(p):\n    """EPUB\'da satır içinde kalmış heceleme tiresi: Merini-ler -> Meriniler (sağ parça tek başına kelime değilse).\n    İzafet (Kur\'an-ı) ve gerçek birleşik yazımlara (Âl-i) dokunulmaz."""\n')
degistir('app/duzelt.py',
    '            return sol + "-" + sag\n        if _kelime_mi(sag) and not listede(sol, sag):\n            return m.group(0)\n        if len(sol) > 3 and len(sag) > 3 and not listede(sol, sag) and not _gecerli_kelime(sol + sag) and _gecerli_kelime(sol) \\\n                and _gecerli_kelime(sag):\n            return m.group(0)   # 0.5.40: ara söz çizgisi (müstesna- yüzlerinizi, göre- örfe): iki kelime de geçerli, birleşik hâl değil\n',
    '            return sol + "-" + sag\n        if _kelime_mi(sag) and not listede(sol, sag):\n            return m.group(0)\n        if not listede(sol, sag) and not _gecerli_kelime(sol + sag) and acik_ara_soz(m.string, m.start(1)):\n            return m.group(0)   # 0.5.40c: açılmış ara sözün kapanış çizgisi (değil- acz, ise- hummalı)\n        if len(sol) > 3 and len(sag) > 3 and not listede(sol, sag) and not _gecerli_kelime(sol + sag) and _gecerli_kelime(sol) \\\n                and _gecerli_kelime(sag):\n            return m.group(0)   # 0.5.40: ara söz çizgisi (müstesna- yüzlerinizi, göre- örfe): iki kelime de geçerli, birleşik hâl değil\n')
degistir('tests/test_bakara_duzeni.py',
    'dene("büyük harfli ek birleşir", S._duzelt(["el-kadîm Û ’İN bir nüktesi"])[0] == "el-kadîm Û’İN bir nüktesi")\n\nprint("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")\n',
    'dene("büyük harfli ek birleşir", S._duzelt(["el-kadîm Û ’İN bir nüktesi"])[0] == "el-kadîm Û’İN bir nüktesi")\n\n# 6) 0.5.40c: açılmış ara sözün kapanış çizgisi, parça kısa olsa da (Kitabü\'t-Tevhid, Âsâr-ı Bediiyye)\ndene("ara söz kapanışı (satır sonu)", TS.join_lines("zaten -dilsizlik değil-\\nacz alternatifine") == "zaten -dilsizlik değil- acz alternatifine")\ndene("ara söz kapanışı (da-)", TS.join_lines("-hakikatini kavramak mümkün olmasa da-\\nâlemin yoktan") == "-hakikatini kavramak mümkün olmasa da- âlemin yoktan")\ndene("ara söz kapanışı (EPUB)", DZ.satir_ici_tireleri_birlestir("Fâtıra –tâbir caiz ise- hummalı bir faaliyetle") == "Fâtıra –tâbir caiz ise- hummalı bir faaliyetle")\ndene("ara söz yoksa kısa parça birleşir", TS.join_lines("düşmanlığı tercih edip taa-\\ntinden yüz") == "düşmanlığı tercih edip taatinden yüz")\n\nprint("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")\n')
print("BITTI")
