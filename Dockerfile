FROM python:3.10-slim

# Set a non-root user
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} appuser && \
    useradd -u ${USER_ID} -g appuser -s /bin/sh -m appuser

# System dependencies (with specific versions and cleanup in the same layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg=7:* \
    libsm6=2:* \
    libxext6=2:* \
    libgl1-mesa-glx=* && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory and adjust permissions
WORKDIR /app
RUN chown -R appuser:appuser /app

# Copy dependencies first (for better caching)
COPY --chown=appuser:appuser requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# Copy the application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose the port
EXPOSE 8000

# Use exec form of CMD for proper signal handling
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]