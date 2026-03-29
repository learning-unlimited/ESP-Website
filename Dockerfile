FROM python:3.7-slim-bullseye AS builder

# Build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /tmp

# Copy and install system dependencies from packages_base.txt
# Prevent interactive popups during apt-get install (e.g., tzdata)
ENV DEBIAN_FRONTEND=noninteractive

# Configure apt-get retries and timeouts for heavy LaTeX downloads
RUN printf '%s\n' \
    'Acquire::http::Timeout "120";' \
    'Acquire::https::Timeout "120";' \
    'Acquire::ftp::Timeout "120";' \
    'Acquire::Retries "3";' > /etc/apt/apt.conf.d/99custom

# Set the working directory
WORKDIR /app

# Install system dependencies from packages_base.txt to avoid duplication.
COPY esp/packages_base.txt /tmp/packages_base.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    curl \
    ghostscript \
    texlive \
    texlive-latex-extra \
    dvipng \
    ca-certificates \
    gnupg \
    libcurl4-openssl-dev \
    libssl-dev \
    libmemcached-dev \
    libevent-dev \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    $(grep -v '^python' /tmp/packages_base.txt | grep -v '^#' | grep -v '^$' | grep -v 'build-essential' | grep -v 'libpq-dev' | grep -v 'libcurl' | grep -v 'libssl' | grep -v 'libmemcached' | grep -v 'libevent' | grep -v 'zlib' | grep -v 'libjpeg' | grep -v 'libfreetype' | tr '\n' ' ') \
    && rm -rf /var/lib/apt/lists/*

# Install LESS via npm (from packages_base_manual_install.sh)
RUN npm install --prefix /usr less@3.13.1 -g

# Install Node.js for LESS
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*
# Install LESS globally
RUN npm install -g less@1.7.5

# Install Python dependencies (Docker layer caching speeds up rebuilds)
COPY esp/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt


# Runtime stage - smaller final image
FROM python:3.7-slim-bullseye AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/usr \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install only runtime dependencies (shared libraries, no -dev packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    git \
    ca-certificates \
    libmemcached11 \
    libcurl4 \
    libssl1.1 \
    libjpeg62-turbo \
    libfreetype6 \
    libevent-2.1-7 \
    zlib1g \
    imagemagick \
    inkscape \
    wamerican-large \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy Node.js and LESS from builder
COPY --from=builder /usr/bin/node /usr/bin/node
COPY --from=builder /usr/lib/node_modules /usr/lib/node_modules
RUN ln -s /usr/lib/node_modules/less/bin/lessc /usr/local/bin/lessc

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh

# Copy application code (will be overridden by volume mount in dev)
COPY esp /app/esp

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver_plus", "0.0.0.0:8000"]
