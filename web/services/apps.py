import logging
import os

from django.apps import AppConfig
from jupyterjsc_unicoremgr.settings import LOGGER_NAME
from services.utils import _config

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"

class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"

    def create_user(self, username, passwd, groups=[], superuser=False, mail=""):
        from django.contrib.auth.models import Group
        from django.contrib.auth.models import User

        if User.objects.filter(username=username).exists():
            return
        log.info(f"Create user {username}", extra={"uuidcode": "StartUp"})
        if superuser:
            User.objects.create_superuser(username, mail, passwd)
            return
        else:
            user = User.objects.create(username=username)
            user.set_password(passwd)
            user.save()
        for group in groups:
            if not Group.objects.filter(name=group).exists():
                Group.objects.create(name=group)
            _group = Group.objects.filter(name=group).first()
            user.groups.add(_group)

    def setup_logger(self):
        from logs.models import HandlerModel

        data = {
            "handler": "stream",
            "configuration": {
                "level": 10,
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
        }
        HandlerModel(**data).save()

    def setup_db(self):
        config = _config()
        user_groups = config.get("startup", {}).get("create_user", {})

        superuser_name = "admin"
        superuser_mail = os.environ.get("SUPERUSER_MAIL", "admin@example.com")
        superuser_pass = os.environ["SUPERUSER_PASS"]
        self.create_user(
            superuser_name, superuser_pass, superuser=True, mail=superuser_mail
        )

        for username, groups in user_groups.items():
            userpass = os.environ.get(f"{username.upper()}_USER_PASS", None)
            if userpass:
                self.create_user(username, userpass, groups=groups)
            else:
                log.info(
                    f"Do not create user {username} - password is missing",
                    extra={"uuidcode": "StartUp"},
                )

    
    def ready(self):
        if os.environ.get("GUNICORN_START", "false").lower() == "true":
            self.setup_logger()
            self.setup_db()
        return super().ready()
