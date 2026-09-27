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
RUN python app/make_icon.py

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
