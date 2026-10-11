"""zeyrek 0.1.3 hatasının düzeltmesi: çözümleme, kök kaydının ses özellikleri kümesini (StemTransition.attrs) kopyalamadan
kullanıyor; ekin yüzeyi kelimenin kalanına eşitse (rulebasedanalyzer: tail_equals_surface) kümeye eklenen özellik
(ör. ExpectsConsonant) kök kaydına kalıcı yazılıyor. Sonuç: "olmak" bir kez çözümlenince "olanlar", "olacak" gibi
"ol-" kökünden doğru kelimeler geçersiz sayılıyor. Düzeltme: arama kök kümesinin kopyasıyla başlar."""
try:
    from zeyrek import morphotactics as _mt

    if not getattr(_mt.SearchPath, "_dedplay_onarim", False):
        _asil_initial = _mt.SearchPath.initial.__func__

        @classmethod
        def _initial(cls, stem_transition, tail):
            yol = _asil_initial(cls, stem_transition, tail)
            yol.phonetic_attributes = set(yol.phonetic_attributes)  # kök kaydının kümesi değil, kopyası
            return yol

        _mt.SearchPath.initial = _initial
        _mt.SearchPath._dedplay_onarim = True
except Exception:  # zeyrek yoksa ya da yapısı değiştiyse dokunma
    pass


# 0.5.36: zeyrek'in iki sıra hatası. Aynı kitap Python'un her açılışında (PYTHONHASHSEED) farklı sonuç veriyordu
# (altın çıktı denetimi, 11 Ekim): "zıddı", "zıddının", "öd" bazı açılışlarda geçersiz sayılıyordu.
# 1) calculate_phonetic_attributes lru_cache'li ve herkese AYNI küme nesnesini veriyor; çağıranlar onu değiştiriyor
#    (ödemek kökü "öd"e inerken LastLetterDropped ekleniyor ve "öd" isim köküne bulaşıyor). Düzeltme: her çağrıya kopya.
# 2) Kök özellikleri (Voicing, Doubling…) kümeden sırasız dolaşılıyor: "zıt" bazen zıt->zıd->zıdd, bazen zıt->zıtt->zıtd.
#    Zemberek'te (Java EnumSet) tanım sırasıyla dolaşılır. Düzeltme: özellik kümesi tanım sırasıyla dolaşılır.
try:
    import sys as _sys
    from zeyrek import attributes as _at, morphotactics as _mt2

    if not getattr(_at, "_dedplay_sira_onarim", False):
        _asil_hesap = _at.calculate_phonetic_attributes

        def _hesap_kopya(word, predecessor_attrs=None):
            return set(_asil_hesap(word, predecessor_attrs))

        _hesap_kopya.cache_info = getattr(_asil_hesap, "cache_info", None)
        for _ad, _mod in list(_sys.modules.items()):
            if _ad == "zeyrek" or _ad.startswith("zeyrek."):
                if getattr(_mod, "calculate_phonetic_attributes", None) is _asil_hesap:
                    _mod.calculate_phonetic_attributes = _hesap_kopya

        def _sira_anahtari(a):
            v = getattr(a, "value", a)
            return (0, v) if isinstance(v, int) else (1, str(v))

        class _SiraliKume(set):
            """Dolaşıldığında tanım sırasını veren küme (Java EnumSet gibi); öteki bütün küme işlemleri aynı."""
            def __iter__(self):
                return iter(sorted(set.__iter__(self), key=_sira_anahtari))

        _asil_gecis = _mt2.StemTransitionsMapBased.generate_transitions

        def _gecis(self, dict_item):
            if not isinstance(dict_item.attributes, _SiraliKume):
                dict_item.attributes = _SiraliKume(dict_item.attributes)
            return _asil_gecis(self, dict_item)

        _mt2.StemTransitionsMapBased.generate_transitions = _gecis
        _at._dedplay_sira_onarim = True
except Exception:  # zeyrek yoksa ya da yapısı değiştiyse dokunma
    pass
