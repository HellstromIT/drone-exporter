FROM python:3.7-alpine

MAINTAINER Martin Hellstrom <martin@hellstrom.it>

WORKDIR /app

COPY requirements.txt ./

RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev &&\
    pip install --no-cache-dir -r requirements.txt

COPY dronedb_exporter.py /dronedb_exporter.py

RUN chmod +x /dronedb_exporter.py

EXPOSE 9698

ENTRYPOINT ["/dronedb_exporter.py"]
