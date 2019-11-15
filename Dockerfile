FROM python:3.6-alpine

WORKDIR /celery
ENV PYTHONUNBUFFERED 0
ENV FLASK_APP app.py
COPY requirements.txt  app.py ./

RUN pip install -r requirements.txt

EXPOSE 8080
CMD flask run --host 0.0.0.0 --port 8080
