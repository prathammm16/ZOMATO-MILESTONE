# Zomato AI — Docker (optional Phase 6)

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ config/
COPY src/ src/
COPY scripts/ scripts/
COPY .streamlit/ .streamlit/
COPY data/.gitkeep data/.gitkeep

# Cache mount at runtime: -v ./data:/app/data
ENV PYTHONPATH=/app
ENV DATA_CACHE_PATH=data/cache.parquet

EXPOSE 8501

# Requires GROQ_API_KEY at runtime: docker run -e GROQ_API_KEY=... -p 8501:8501
CMD ["streamlit", "run", "src/ui/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
