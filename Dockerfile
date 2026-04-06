FROM python:3.7-slim-bullseye AS builder

# Build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set the working directory
WORKDIR /app

# Install only build-time dependencies (compilers, -dev headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    curl \
    ca-certificates \
    gnupg \
    libcurl4-openssl-dev \
    libssl-dev \
    libmemcached-dev \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js from nodesource, then LESS
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g --prefix /usr less@3.13.1

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

# Configure apt-get retries and timeouts for heavy LaTeX downloads
RUN printf '%s\n' \
    'Acquire::http::Timeout "120";' \
    'Acquire::https::Timeout "120";' \
    'Acquire::ftp::Timeout "120";' \
    'Acquire::Retries "3";' > /etc/apt/apt.conf.d/99custom

# Install runtime dependencies:
#   - Slim runtime libraries (counterparts of builder's -dev packages)
#   - Runtime tools from packages_base.txt (filtering out python*, build-essential, git, postgres*, memcached, and -dev packages)
COPY esp/packages_base.txt /tmp/packages_base.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    libmemcached11 \
    libcurl4 \
    libssl1.1 \
    libjpeg62-turbo \
    libfreetype6 \
    zlib1g \
    ca-certificates \
    $(grep -v -E '^(#|$|python|build-essential|git|postgres|memcached)' /tmp/packages_base.txt | grep -v -- '-dev$' | tr '\n' ' ') \
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
