###############################################################################
# Build stage
# Creation date: 21/12/2017
# Author: eltonplima
###############################################################################
FROM python:2.7-alpine3.7 as builder

WORKDIR /home/app
RUN apk update && apk upgrade && apk add alpine-sdk postgresql-dev libffi-dev libxml2-dev py-virtualenv libxslt-dev
RUN apk add gdal gdal-dev --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
RUN pip install virtualenv
RUN virtualenv -p python2.7 env
COPY . .
RUN ./env/bin/pip install -r pip-freeze.txt && ./env/bin/pip install -U psycopg2

###############################################################################
# Deploy stage
###############################################################################
FROM python:2.7-alpine3.7

WORKDIR /home/app
RUN apk update && apk upgrade
RUN apk add libpq libxml2 libxslt libmagic
RUN apk add gdal --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
COPY --from=builder /home/app .
RUN pip install gunicorn supervisor
EXPOSE 8000
ENTRYPOINT /usr/local/bin/supervisord
