FROM python:3.9-slim as base

# Setup env
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1
ENV KAFKA_VERSION 1.6.0

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    inotify-tools \
    libpq-dev \
    wget \
    curl \ 
    gcc \
    # python3-dev \
    musl-dev \
    build-essential \
    ca-certificates \
    git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists*

RUN wget https://github.com/edenhill/librdkafka/archive/v${KAFKA_VERSION}.tar.gz \
    && tar xvzf v${KAFKA_VERSION}.tar.gz \
    && cd librdkafka-${KAFKA_VERSION}/ \
    && ./configure && make && make install && ldconfig

WORKDIR /app

RUN pip install --upgrade pip && pip install pipenv
RUN echo "if [[ -z \"\${VIRTUAL_ENV}\" ]]; then" >> /root/.bashrc && \
    echo "source \$(pipenv --venv)/bin/activate" >> /root/.bashrc && \
    echo "fi"                                    >> /root/.bashrc

COPY scripts/ /opt/bin/
COPY . /app

RUN pipenv --venv > /dev/null || pipenv install --skip-lock --ignore-pipfile --python $(which python)

EXPOSE 5000

CMD ["pipenv", "run", "server"]