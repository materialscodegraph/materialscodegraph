# MaterialsCodeGraph-lite Docker Image
FROM python:3.9-slim

LABEL maintainer="MaterialsCodeGraph Contributors <mcg@example.com>"
LABEL description="MaterialsCodeGraph-lite: MCP-based materials science workflows"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install MCG-lite in development mode
RUN pip install -e .

# Create non-root user for security
RUN groupadd -r mcg && useradd -r -g mcg mcg

# Create data directory
RUN mkdir -p /opt/mcg/data && chown -R mcg:mcg /opt/mcg

# Switch to non-root user
USER mcg

# Set environment variables
ENV MCG_STORAGE_PATH=/opt/mcg/data
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port for MCP servers
EXPOSE 8000 8001 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import interfaces_mcp.server; print('OK')" || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "memory_mcp.server"]

# Metadata
LABEL org.opencontainers.image.source="https://github.com/your-org/materialscodegraph-lite"
LABEL org.opencontainers.image.description="MaterialsCodeGraph-lite: Minimal MCP implementation for materials science"
LABEL org.opencontainers.image.licenses="MIT"