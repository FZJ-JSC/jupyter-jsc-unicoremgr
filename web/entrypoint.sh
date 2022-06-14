#!/bin/bash

USERNAME=unicoremgr

# Set secret key
export SECRET_KEY=${SECRET_KEY:-$(uuidgen)}


# Database setup / wait for database
if [ "$SQL_ENGINE" == "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
        sleep 0.1
    done
    echo "$(date) PostgreSQL started"
fi
export SUPERUSER_PASS=${SUPERUSER_PASS:-$(uuidgen)}
su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py makemigrations"
su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py migrate"
echo "$(date) Admin password: ${SUPERUSER_PASS}"

if [[ ! -d /home/${USERNAME}/web/static ]]; then
    echo "$(date) Collect static files ..."
    su ${USERNAME} -c "SQL_DATABASE=/dev/null python3 /home/${USERNAME}/web/manage.py collectstatic"
    echo "$(date) Collect static files ... done"
fi

if [ -z ${GUNICORN_PATH} ]; then
    export GUNICORN_SSL_CRT=${GUNICORN_SSL_CRT:-/home/${USERNAME}/certs/${USERNAME}.crt}
    export GUNICORN_SSL_KEY=${GUNICORN_SSL_KEY:-/home/${USERNAME}/certs/${USERNAME}.key}
    if [[ -f ${GUNICORN_SSL_CRT} && -f ${GUNICORN_SSL_KEY} ]]; then
        GUNICORN_PATH=/home/${USERNAME}/web/gunicorn_https.py
        echo "Use ${GUNICORN_PATH} as config file. Service will listen on port 8443."
        echo "Use these files for ssl: ${GUNICORN_SSL_CRT}, ${GUNICORN_SSL_KEY}"
    else
        GUNICORN_PATH=/home/${USERNAME}/web/gunicorn_http.py
        echo "Use ${GUNICORN_PATH} as config file. Service will listen on port 8080."
    fi
fi

# Set Defaults for gunicorn and start
export GUNICORN_PROCESSES=${GUNICORN_PROCESSES:-16}
export GUNICORN_THREADS=${GUNICORN_THREADS:-1}
gunicorn -c ${GUNICORN_PATH} jupyterjsc_unicoremgr.wsgi
