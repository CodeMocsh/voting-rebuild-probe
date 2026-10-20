FROM python:3.11-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local/app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS dev
RUN pip install --no-cache-dir pytest==8.3.3 watchdog==5.0.3
ENV FLASK_ENV=development
CMD ["gunicorn", "vote.app:app", "-b", "0.0.0.0:80", "--reload", "--log-file", "-", "--access-logfile", "-"]

FROM dev AS browser
RUN pip install --no-cache-dir playwright==1.47.0 && \
    playwright install --with-deps chromium

FROM base AS final

COPY . ./vote/

EXPOSE 80

CMD ["gunicorn", "vote.app:app", "-b", "0.0.0.0:80", "--log-file", "-", "--access-logfile", "-", "--workers", "4", "--keep-alive", "0"]
