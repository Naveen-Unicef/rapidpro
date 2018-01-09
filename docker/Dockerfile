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
RUN ./env/bin/pip install -r requirements.txt && ./env/bin/pip install -U psycopg2

###############################################################################
# Deploy stage
###############################################################################
FROM python:2.7-alpine3.7

WORKDIR /home/app
RUN apk update && apk upgrade
RUN apk add libpq libxml2 libxslt libmagic nodejs yarn
RUN apk add gdal geos --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/
RUN yarn global add coffeescript less
RUN yarn install
COPY --from=builder /home/app .
RUN env/bin/python manage.py collectstatic --noinput
RUN pip install gunicorn supervisor
RUN touch ngrok.yml && mkdir /root/.ngrok2
#COPY ngrok.yml /root/.ngrok2/
EXPOSE 8000
RUN chmod +x docker/entrypoint.sh
ENTRYPOINT /home/app/docker/entrypoint.sh
