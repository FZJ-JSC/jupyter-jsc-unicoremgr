import logging
import uuid

from django.urls.base import reverse
from jupyterjsc_unicoremgr.settings import LOGGER_NAME
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from services.utils import MgrException

from .models import ServicesModel
from .utils import get_custom_headers
from .utils.common import instance_dict_and_custom_headers_to_logs_extra
from .utils.common import status_service

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicesModel
        fields = [
            "id",
            "servername",
            "start_id",
            "user_options",
            "jhub_user_id",
            "jhub_credential",
            "start_date",
            "stop_pending",
        ]

    def check_input_keys(self, required_keys):
        for key, values in required_keys.items():
            if key not in self.initial_data.keys():
                self._validated_data = []
                self._errors = [f"Missing key in input data: {key}"]
                raise ValidationError(self._errors)
            for value in values:
                if value not in self.initial_data[key].keys():
                    self._validated_data = []
                    self._errors = [f"Missing key in input data: {key}.{value}"]
                    raise ValidationError(self._errors)
        custom_headers = get_custom_headers(self.context["request"]._request.META)
        if "access-token" not in custom_headers:
            self._validated_data = []
            self._errors = ["Missing key in headers: access-token"]
            raise ValidationError(self._errors)

    def is_valid(self, raise_exception=False):
        required_keys = {
            "env": [
                "JUPYTERHUB_STATUS_URL",
                "JUPYTERHUB_API_TOKEN",
                "JUPYTERHUB_USER_ID",
            ],
            "user_options": ["vo", "partition", "project", "service", "system"],
            "start_id": [],
        }
        try:
            self.check_input_keys(required_keys)
        except ValidationError as exc:
            _errors = exc.detail
        else:
            _errors = {}
        if _errors and raise_exception:
            raise ValidationError(_errors)
        return super().is_valid(raise_exception=raise_exception)

    def to_internal_value(self, data):
        custom_headers = get_custom_headers(self.context["request"]._request.META)
        model_data = {
            "servername": custom_headers.get("uuidcode", uuid.uuid4().hex),
            "start_id": data["start_id"],
            "user_options": data["user_options"],
            "jhub_user_id": data["env"]["JUPYTERHUB_USER_ID"],
            "jhub_credential": self.context["request"].user.username,
            "stop_pending": False,
        }
        return super().to_internal_value(model_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # For create or list we don't want to update status
        if self.context["request"].path == reverse("services-list"):
            return ret
        custom_headers = get_custom_headers(self.context["request"]._request.META)
        logs_extra = instance_dict_and_custom_headers_to_logs_extra(
            instance.__dict__, custom_headers
        )
        logs_extra["start_date"] = ret["start_date"]

        if instance.stop_pending:
            log.debug("Service is already stopping. Return false", extra=logs_extra)
            status = {"running": False}
        elif "access-token" not in custom_headers.keys():
            log.debug("No access token available. Return true", extra=logs_extra)
            status = {"running": True}
        else:
            try:
                status = status_service(
                    instance.__dict__,
                    custom_headers,
                    logs_extra=logs_extra,
                )
            except MgrException as e:
                log.critical(
                    "Could not check status of service", extra=logs_extra, exc_info=True
                )
                status = {
                    "running": True,
                    "details": {"error": e.args[0], "detailed_error": e.args[1]},
                }
        if not status:
            status = {"running": True}
        ret.update(status)
        return ret
