FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 fonts-noto-core fontconfig tesseract-ocr tesseract-ocr-tur \
    && rm -rf /var/lib/apt/lists/*
ADD https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/tur.traineddata /tmp/tur_best.traineddata
RUN cp /tmp/tur_best.traineddata "$(dirname "$(find /usr/share/tesseract-ocr -name tur.traineddata | head -1)")/tur.traineddata" && rm /tmp/tur_best.traineddata  # tessdata_best: daha isabetli Türkçe OCR
ADD https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf /usr/share/fonts/truetype/amiri/Amiri-Regular.ttf
ADD https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Bold.ttf /usr/share/fonts/truetype/amiri/Amiri-Bold.ttf
RUN chmod 644 /usr/share/fonts/truetype/amiri/*.ttf && fc-cache -f

ENV PYTHONUNBUFFERED=1 DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ADD https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/tr/tr_50k.txt /app/app/data/tr_kelime.txt
RUN python app/make_icon.py

# ---- Tek uygulama: Kütüphane (OCR, temizlik, EPUB) aynı imajda ----
# epubcheck (W3C resmî EPUB denetimi) için Java
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*
ADD https://github.com/w3c/epubcheck/releases/download/v5.4.0/epubcheck-5.4.0.zip /tmp/epubcheck.zip
RUN python -c "import zipfile; zipfile.ZipFile('/tmp/epubcheck.zip').extractall('/opt')" && rm /tmp/epubcheck.zip \
    && java -jar /opt/epubcheck-5.4.0/epubcheck.jar --version
# OCR motoru: Surya 0.14.7 (işlemcide). torch/torchvision işlemci sürümü, birlikte yeniden kurulur. Surya 0.15+ kullanılmaz.
RUN pip install --no-cache-dir "surya-ocr==0.14.7" "pillow<11" \
    && pip install --no-cache-dir --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cpu
ENV EPUBCHECK=/opt/epubcheck-5.4.0/epubcheck.jar FONT_DIR=/usr/share/fonts/truetype/amiri \
    OCR_MOTORU=surya MODEL_CACHE_DIR=/data/modeller/surya TORCH_DEVICE=cpu \
    STUDYO_DATA_DIR=/studyo-data
COPY kutuphane ./kutuphane
# Kütüphane verisi /data (kitaplar, OCR önbelleği, Surya modelleri), Stüdyo verisi /studyo-data
EXPOSE 8000
CMD ["uvicorn", "app.birlesik:app", "--host", "0.0.0.0", "--port", "8000"]
