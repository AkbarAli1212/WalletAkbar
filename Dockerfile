# ==============================================================================
# Production Dockerfile for BudgetBakers Wallet Telegram Bot
# ==============================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Riyadh \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install timezone data & certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    ca-certificates \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Create application directory and non-root user
WORKDIR /app
RUN useradd -m -u 1000 appuser

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY config.py parser.py wallet_client.py bot.py get_metadata.py ./

# Switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Run bot
CMD ["python", "bot.py"]
