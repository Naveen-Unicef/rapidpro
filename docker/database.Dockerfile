FROM mdillon/postgis:9.3-alpine
RUN apk update
RUN apk upgrade
COPY database.sh /docker-entrypoint-initdb.d/
