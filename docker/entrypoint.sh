#!/bin/sh
/home/app/env/bin/python /home/app/manage.py migrate
/usr/local/bin/supervisord
