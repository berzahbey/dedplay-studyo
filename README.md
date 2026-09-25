# Dedplay Studio

Kitabı bir kez ver, gerisini Stüdyo halleder:

1. Kitap Türkçe değilse **Dedplay Translate** Türkçeye çevirir.
2. Çeviri bitince (ya da kitap zaten Türkçeyse hemen) **Dedplay Kitap Okuma** seslendirir,
   aynı anda **Osmanlıca çevirici** temiz metin parçalarını Osmanlıcaya aktarır.
3. Sonuç tek sayfada: M4B sesli kitap, Türkçe ve Osmanlıca EPUB / PDF / Word / HTML / TXT.

Stüdyo diğer üç uygulamayı HTTP üzerinden yönetir; onların çalışıyor olması gerekir.

## Kurulum

```bash
git clone https://github.com/berzahbey/dedplay-studyo.git /DATA/AppData/dedplay-studyo/kaynak
cd /DATA/AppData/dedplay-studyo/kaynak
docker compose up -d --build
```

Adres: `http://<sunucu-ip>:8070`

## Ayarlar (docker-compose.yml)

- `TRANSLATE_URL`, `OKUMA_URL`, `OSMANLICA_URL`: diğer uygulamaların adresleri
- `OSM_USE_OLLAMA`: Osmanlıca çevirici bilinmeyen kelimelerde Ollama kullansın mı (varsayılan `false`)
- `/okuma-text`: Kitap Okuma'nın `text` klasörü (salt okunur)
- `/kaynak`: sunucudan kitap seçmek için kitap arşivi (salt okunur)
