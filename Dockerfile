# lightweight python image
FROM python:3.10-slim-buster

#  working directory inside the container
WORKDIR /app

# prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy only the service files
COPY config.yml .
COPY state.json .
COPY src/ ./src/

# set environment variables default 
ENV PYTHONPATH=/app/src:/app

# run the scraper monitor
CMD ["python", "src/main.py"]
