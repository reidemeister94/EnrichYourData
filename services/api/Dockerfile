FROM python:3.8.8-slim-buster

ENV WORKDIR=/usr/src/app
ENV USER=app
ENV APP_HOME=/home/app/api
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR $WORKDIR

RUN pip install --upgrade pip
RUN apt-get update -y && apt-get install -y curl
# Install Poetry
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Copy using poetry.lock* in case it doesn't exist yet
COPY ./app/pyproject.toml ./app/poetry.lock* $WORKDIR/

RUN poetry install --no-root --no-dev

RUN adduser --system --group $USER
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

RUN chown -R $USER:$USER $APP_HOME
USER $USER