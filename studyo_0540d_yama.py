# Stüdyo 0.5.40d: ara söz kapanışı yalnız sağ parça kendi başına kelimeyse (cismiyetle- rinden -> cismiyetlerinden)
import sys
DEGISIKLIK = [
    ("app/textsrc.py",
     "        if not _dz._gecerli_kelime(sol + sag) and _dz.acik_ara_soz(m.string, m.start(1)):\n",
     "        if not _dz._gecerli_kelime(sol + sag) and _dz.acik_ara_soz(m.string, m.start(1)) \\\n"
     "                and (_dz._gecerli_kelime(sag) or _dz._kelime_mi(sag) or sag[:1].isupper()):   # 0.5.40d: \"rinden\" ek, kelime değil\n"),
    ("app/duzelt.py",
     "        if not listede(sol, sag) and not _gecerli_kelime(sol + sag) and acik_ara_soz(m.string, m.start(1)):\n",
     "        if not listede(sol, sag) and not _gecerli_kelime(sol + sag) and acik_ara_soz(m.string, m.start(1)) \\\n"
     "                and (_gecerli_kelime(sag) or _kelime_mi(sag) or sag[:1].isupper()):   # 0.5.40d\n"),
    ("tests/test_bakara_duzeni.py",
     "\nprint(\"SONUC: HEPSI GECTI\"",
     "\n# 7) 0.5.40d: ara söz içinde de sağ parça ekse (kelime değilse) hece bölünmesidir\n"
     "dene(\"ara söz içinde hece bölünmesi (satır sonu)\", TS.join_lines(\"çoğunun -ki bunlar cismiyetle-\\nrinden söz edilmesine\") == \"çoğunun -ki bunlar cismiyetlerinden söz edilmesine\")\n"
     "dene(\"ara söz içinde hece bölünmesi (EPUB)\", DZ.satir_ici_tireleri_birlestir(\"çoğunun -ki bunlar cismiyetle- rinden söz\") == \"çoğunun -ki bunlar cismiyetlerinden söz\")\n"
     "dene(\"ara söz kapanışı büyük harf\", TS.join_lines(\"-Açıklamalı Tercüme-\\nEbû Mansur\") == \"-Açıklamalı Tercüme- Ebû Mansur\")\n"
     "\nprint(\"SONUC: HEPSI GECTI\""),
]
for yol, eski, yeni in DEGISIKLIK:
    m = open(yol, encoding="utf-8").read()
    if yeni in m:
        print("ATLANDI (zaten var):", yol); continue
    if m.count(eski) != 1:
        print("HATA:", yol, "beklenen metin", m.count(eski), "kez bulundu"); sys.exit(1)
    open(yol, "w", encoding="utf-8").write(m.replace(eski, yeni))
    print("TAMAM:", yol)
print("BITTI")
