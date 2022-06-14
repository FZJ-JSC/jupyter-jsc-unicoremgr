FROM python:3.8.12-alpine3.14

ENV USERNAME=unicoremgr

# create the app user
RUN adduser --uid 1000 --ingroup users --gecos "" --disabled-password ${USERNAME}

# create the appropriate directories
ENV HOME=/home/${USERNAME}
ENV APP_HOME=/home/${USERNAME}/web
RUN mkdir -p ${APP_HOME} && mkdir -p ${HOME}/certs
WORKDIR ${APP_HOME}

RUN apk update && \
    apk upgrade && \
    pip install -U pip
    
# Install app requirements
COPY ./requirements_pip.txt /tmp/requirements_pip.txt
COPY ./requirements_apk.txt /tmp/requirements_apk.txt
RUN apk add --virtual=build_dependencies build-base && \
    cat /tmp/requirements_apk.txt | xargs apk add && \
    pip install -r /tmp/requirements_pip.txt && \
    apk del --purge -r build_dependencies && \
    chown -R ${USERNAME}:users ${HOME} && \
    rm /tmp/requirements_pip.txt && \
    rm /tmp/requirements_apk.txt

# copy project
COPY web ${APP_HOME}

# chown all the files to the app user
RUN chown -R ${USERNAME}:users ${APP_HOME}

ENTRYPOINT ["/home/unicoremgr/web/entrypoint.sh"]
