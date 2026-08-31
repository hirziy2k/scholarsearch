FROM python:3.14-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .

FROM python:3.14-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    fonts-dejavu-core \
    fontconfig \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    cabextract \
    wget \
    && wget -q https://downloads.sourceforge.net/corefonts/times32.exe \
    && cabextract times32.exe -d /usr/share/fonts/truetype/msttcorefonts/ \
    && rm times32.exe \
    && wget -q https://downloads.sourceforge.net/corefonts/arial32.exe \
    && cabextract arial32.exe -d /usr/share/fonts/truetype/msttcorefonts/ \
    && rm arial32.exe \
    && wget -q https://downloads.sourceforge.net/corefonts/courie32.exe \
    && cabextract courie32.exe -d /usr/share/fonts/truetype/msttcorefonts/ \
    && rm courie32.exe \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

RUN groupadd -r pptxuser && useradd -r -g pptxuser -d /app -s /sbin/nologin pptxuser

WORKDIR /app

RUN chown -R pptxuser:pptxuser /app

USER pptxuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

ENTRYPOINT ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
