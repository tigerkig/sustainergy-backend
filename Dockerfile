FROM ubuntu:20.04

RUN apt-get update && apt-get install apt-utils && \
apt-get install libpangocairo-1.0.0 -y && \
apt-get -y install net-tools python3.8 python3-pip mysql-client libmysqlclient-dev git && \
apt-get -y install python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 && \
apt-get -y install apt-utils && apt-get -y upgrade

RUN apt-get -y install wget && apt-get -y install gdebi && \
wget "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.focal_amd64.deb" && \
apt install -y ./wkhtmltox_0.12.6-1.focal_amd64.deb

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app

RUN pip3 install -r requirements.txt && pip3 install awsebcli --upgrade --user

CMD python3 manage.py runserver 0.0.0.0:8000
