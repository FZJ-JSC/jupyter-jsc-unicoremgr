# J4J_UNICORE

FROM ubuntu:18.04

RUN apt update && apt install -y ssh && apt install -y python3 && apt install -y python3-pip && apt install -y net-tools && apt install -y inotify-tools && DEBIAN_FRONTEND=noninteractive apt install -y tzdata && ln -fs /usr/share/zoneinfo/Europe/Berlin /etc/localtime && dpkg-reconfigure -f noninteractive tzdata

RUN pip3 install flask-restful==0.3.7 uwsgi==2.0.17.1 

RUN mkdir -p /etc/j4j/J4J_UNICORE

RUN adduser --disabled-password --gecos '' unicore

RUN chown unicore:unicore /etc/j4j/J4J_UNICORE

USER unicore

COPY --chown=unicore:unicore ./app /etc/j4j/J4J_UNICORE/app

COPY --chown=unicore:unicore ./app.py /etc/j4j/J4J_UNICORE/app.py

COPY --chown=unicore:unicore ./scripts /etc/j4j/J4J_UNICORE

COPY --chown=unicore:unicore ./uwsgi.ini /etc/j4j/J4J_UNICORE/uwsgi.ini

WORKDIR /etc/j4j/J4J_UNICORE

CMD /etc/j4j/J4J_UNICORE/start.sh
