FROM python:3.9-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev make \
    && rm -rf /var/lib/apt/lists/*


COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
COPY ./app /app
COPY ./tests tests/

ENV PYTHONPATH=.

CMD ["gunicorn", "-b", "0.0.0.0:8000", "wsgi:app", "-k", "gevent"]