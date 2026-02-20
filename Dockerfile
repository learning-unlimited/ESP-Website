FROM python:3.7-bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    dvipng \
    git \
    imagemagick \
    libcurl4-openssl-dev \
    libevent-dev \
    libfreetype6-dev \
    libjpeg-dev \
    libmemcached-dev \
    libpq-dev \
    libssl-dev \
    nodejs \
    npm \
    texlive \
    texlive-latex-extra \
    zlib1g-dev \
    && npm install -g less@1.7.5 \
    && rm -rf /var/lib/apt/lists/*

COPY esp/requirements.txt /tmp/requirements.txt
RUN python -m venv "${VIRTUAL_ENV}" && \
    python -m pip install --upgrade pip setuptools==57.5.0 wheel==0.38.4 && \
    python -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY docker/entrypoint.sh /usr/local/bin/esp-entrypoint
RUN chmod +x /usr/local/bin/esp-entrypoint

ENTRYPOINT ["esp-entrypoint"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
