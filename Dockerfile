FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project source files
COPY task1_merge.py .
COPY task2_graphs.py .
COPY api.py .
COPY index.html .
COPY mrt_updates.parquet .
COPY updates.parquet .

# Create directories that will be mounted at runtime
RUN mkdir -p /app/data \
    /app/mrt-data \
    /app/output/task2

EXPOSE 5000

CMD ["python", "api.py"]
