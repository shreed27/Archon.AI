FROM debian:bookworm-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ARCHON_HOME=/app
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-dev \
    python3-pip \
    build-essential \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv $VIRTUAL_ENV

WORKDIR $ARCHON_HOME

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir boto3 amazon-transcribe

# Copy source code and config
COPY src/ ./src/
COPY pyproject.toml .
COPY README.md .
COPY .archon.md .

# Install Archon
RUN pip install --no-cache-dir -e .

# Entrypoint to 'archon' command
ENTRYPOINT ["archon"]
CMD ["start", "/workspace"]
