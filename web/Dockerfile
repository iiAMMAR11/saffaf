# syntax=docker/dockerfile:1
# صفّاف — the trial service. Build from the repository root:
#   docker build -f web/Dockerfile -t saffaf-web .
#   docker run --rm -p 8000:8000 saffaf-web          → http://127.0.0.1:8000
# Ubuntu 24.04 ships LibreOffice 24.2.7.2, the version claude.ai runs and the engine's tests target.
FROM docker.io/library/ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      libreoffice-writer python3 python3-venv poppler-utils fontconfig fonts-liberation fonts-dejavu-core procps \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY web/requirements.txt web/requirements.txt
# extra_ca (optional build secret): a CA bundle for builds behind an intercepting proxy; not stored in the image
RUN --mount=type=secret,id=extra_ca sh -c 'python3 -m venv /opt/venv \
      && if [ -f /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi \
      && /opt/venv/bin/pip install --no-cache-dir -r web/requirements.txt'
ENV PATH=/opt/venv/bin:$PATH
COPY skill skill
COPY tests tests
COPY web web
# The skill's fonts, installed once for the whole system — the same files, unmodified (the engine would otherwise copy
# them into a per-job folder and rebuild fontconfig's cache on every document). The weight rule is the one make.py
# writes for Traditional Arabic Bold: it tells fontconfig what the font's own style name says; the file is not touched.
RUN mkdir -p /usr/share/fonts/saffaf \
    && find skill/saffaf/assets -iname '*.ttf' -exec cp {} /usr/share/fonts/saffaf/ \; \
    && printf '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><match target="scan"><test name="family"><string>Traditional Arabic</string></test><test name="style"><string>Bold</string></test><edit name="weight" mode="assign"><const>bold</const></edit></match></fontconfig>' \
       > /etc/fonts/conf.d/99-saffaf-weight.conf \
    && fc-cache -f
RUN useradd --create-home --shell /usr/sbin/nologin saffaf && mkdir -p /var/saffaf-jobs && chown saffaf /var/saffaf-jobs
USER saffaf
ENV SAFFAF_FONTS_INSTALLED=1 SAFFAF_JOBS_DIR=/var/saffaf-jobs SAFFAF_WORKERS=2 SAFFAF_JOB_TTL=3600
EXPOSE 8000
WORKDIR /app/web
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
