FROM mdillon/postgis:10-alpine
RUN apk update
RUN apk upgrade
COPY database.sh /docker-entrypoint-initdb.d/
