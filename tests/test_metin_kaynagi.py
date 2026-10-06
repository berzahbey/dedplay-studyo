"""Metni zaten olan kaynak (EPUB/DOCX/TXT/yapıştırılan metin): hatasız kitap bozulmamalı (orijinale sadakat).
OCR onarımları (satır sonu tiresi birleştirme, bölünmüş kelime birleştirme, harf onarımı) yalnız metinde o bozukluğun izi
varsa yapılır. Çalıştırma: docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_metin_kaynagi.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
kok = tempfile.mkdtemp()
os.environ.setdefault("DATA_DIR", os.path.join(kok, "k"))
os.environ.setdefault("STUDYO_DATA_DIR", os.path.join(kok, "s"))
os.makedirs(os.environ["STUDYO_DATA_DIR"], exist_ok=True)
from app import birlesik  # noqa: F401
from kutuphane import kaynak

B = []


def ok(k, ad):
    B.append(bool(k))
    print(("GECTI " if k else "KALDI ") + ad)


def metin(kit):
    return "\n".join(b["metin"]["tr"] for b in kit["bloklar"])


siradan = ("Bu kitapta insanın kalbi, aklı ve ruhu için çok güzel dersler vardır. Her gün okunan bu sayfalar, "
            "okuyanın gözünü açar ve ona yeni bir bakış kazandırır. Eski zamanlardan beri bilinen bu yol, bugün de "
            "aynı şekilde devam etmektedir ve herkes kendi payına düşeni alır. ")
temiz = (siradan * 3 + "Vâcib-ül Vücud hakkında bürhan budur. Her şey, bir şey ve hiçbir şey O'nun mana-yı harfiyle "
         "bakar. Bu müvazene ve nümune, mu'cize-i Kur'aniyenin bir lem'asıdır. ") * 30 + "Söz gider- fiilinde kalmaz. "
yol = os.path.join(kok, "Temiz Kitap.txt")
open(yol, "w", encoding="utf-8").write(temiz)
kit = kaynak.cevir(yol)
m = metin(kit)
ok(kit["kunye"]["cikarma"]["onarim"] == {"tire": False, "bolunmus": False, "harf": False}, "temiz metinde onarım yok")
for k in ["Vâcib-ül", "mana-yı", "bürhan", "müvazene", "nümune", "mu'cize-i", "Her şey", "bir şey", "hiçbir şey", "gider- fiilinde"]:
    ok(k in m, f"korundu: {k}")

bozuk = ("Bu kitap- ların tamamı oku- nur ve anla- şılır; oldu ğundan söz edil- miştir. ") * 60
yol = os.path.join(kok, "Bozuk Kitap.txt")
open(yol, "w", encoding="utf-8").write(bozuk)
kit = kaynak.cevir(yol)
m = metin(kit)
ok(kit["kunye"]["cikarma"]["onarim"]["tire"] and kit["kunye"]["cikarma"]["onarim"]["bolunmus"], "bozuk metinde tire ve bölünme onarımı açık")
ok("kitapların" in m and "okunur" in m and "olduğundan" in m, "bozuk metin onarıldı (kitapların, okunur, olduğundan)")

print("SONUC:", "HEPSI GECTI" if all(B) else f"{B.count(False)} TEST KALDI")
sys.exit(0 if all(B) else 1)
