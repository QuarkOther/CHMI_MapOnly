FROM python:3.13-slim

WORKDIR /app
ENV PYTHONPATH=/app/src

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY web ./web
COPY conf ./conf

EXPOSE 8000

# Výchozí příkaz spustí viewer; downloader si příkaz přepíše v compose.
CMD ["python", "-m", "chmi_radar.serve"]
