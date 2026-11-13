"""0.5.78: kuyruk küçük kitabı öne alır."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
from kutuphane import depo  # noqa: E402


def test_kucuk_once(monkeypatch):
    d = tempfile.mkdtemp()
    boy = {"buyuk": 5000, "kucuk": 10, "orta": 900}
    for k, n in boy.items():
        with open(os.path.join(d, k), "wb") as f:
            f.write(b"x" * n)
    monkeypatch.setattr(depo, "kitap_yolu", lambda kid: os.path.join(d, kid))
    q = depo._KucukOnce()
    for k in ("buyuk", "kucuk", "orta", "yok"):
        q.put(("dosya", k, None, 0))
    assert [q.get()[1] for _ in range(4)] == ["yok", "kucuk", "orta", "buyuk"]


def test_koken_bekleyenler(monkeypatch):
    import json
    d = tempfile.mkdtemp()
    for kid, durum in (("a", "gunluk_sinir"), ("b", "tamam"), ("c", None)):
        os.makedirs(os.path.join(d, kid))
        with open(os.path.join(d, kid, "kitap.json"), "w") as f:
            json.dump({"kunye": {"koken": {"durum": durum}}} if durum else {"kunye": {}}, f)
    monkeypatch.setattr(depo, "KITAPLAR", d)
    monkeypatch.setattr(depo, "kitap_yolu", lambda kid: os.path.join(d, kid, "kitap.json"))
    assert depo.koken_bekleyenler() == ["a"]
