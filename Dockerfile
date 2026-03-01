FROM ghcr.io/astral-sh/uv:python3.9-trixie

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

RUN mkdir -p /etc/sudoers.d/

# Set the working directory
WORKDIR /app

RUN groupadd --gid 1000 devuser \
    && useradd --uid 1000 --gid devuser --shell /bin/bash --create-home devuser \
    && echo devuser ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/devuser \
    && chmod 0440 /etc/sudoers.d/devuser

# Install system dependencies from packages_base.txt to avoid duplication.
COPY esp/packages_base.txt /tmp/packages_base.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    $(cat /tmp/packages_base.txt | grep -v '^python' | grep -v '^#' | tr '\n' ' ') \
    && rm -rf /var/lib/apt/lists/*

# Install LESS via npm (from packages_base_manual_install.sh)
RUN npm install --prefix /usr less@1.7.5 -g

# Copy requirements first for better Docker layer caching
COPY esp/pyproject.toml /app/esp/pyproject.toml

# Install Python dependencies
RUN uv pip install -r /app/esp/pyproject.toml --system

# Copy the rest of the application code
COPY . /app

# Copy the entrypoint script and make it executable
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh

USER devuser

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver_plus", "0.0.0.0:8000"]
