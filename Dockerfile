FROM python:3.8.0-slim-buster

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN adduser --disabled-password --gecos '' app-user

RUN mkdir -p /opt/lms/
RUN chown -R app-user:app-user /opt/lms

USER app-user
COPY . /opt/lms/.
WORKDIR /opt/lms
