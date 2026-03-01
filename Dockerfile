FROM python:3.7-bullseye

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Skip manage.py's virtualenv activation hack
ENV VIRTUAL_ENV=/usr

# Set the working directory
WORKDIR /app

# Install system dependencies from packages_base.txt to avoid duplication.
COPY esp/packages_base.txt /tmp/packages_base.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    $(cat /tmp/packages_base.txt | grep -v '^python' | grep -v '^#' | tr '\n' ' ') \
    && rm -rf /var/lib/apt/lists/*

# Install LESS via npm (from packages_base_manual_install.sh)
RUN npm install --prefix /usr less@1.7.5 -g

# Copy requirements first for better Docker layer caching
COPY esp/requirements.txt /app/esp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r /app/esp/requirements.txt

# Copy the rest of the application code
COPY . /app

# Copy the entrypoint script and make it executable
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh

# Expose the Django development server port
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver_plus", "0.0.0.0:8000"]
