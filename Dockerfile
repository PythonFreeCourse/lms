FROM python:3.8.0-slim-buster

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

RUN mkdir -p /opt/lms/
COPY . /opt/lms/.
WORKDIR /opt/lms
