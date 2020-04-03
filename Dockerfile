FROM tiangolo/meinheld-gunicorn-flask:python3.6

ARG PORT

RUN apt-get update && apt-get install -y fluidsynth && rm -rf /var/lib/apt/lists/*

RUN rm -rf /app/app
RUN rm -rf /app/*
ADD rmuse_app /app
ADD . /repo

RUN cd /repo/ ; pip install --no-cache-dir -e . && rm -rf ~/.cache

ENV MODULE_NAME="main"
ENV LOG_LEVEL="debug"
ENV PORT=$PORT
ENV WEB_CONCURRENCY=1
