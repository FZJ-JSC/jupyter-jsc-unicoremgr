import copy
import logging
import uuid

from jupyterjsc_unicoremgr.settings import LOGGER_NAME
from services.utils import _config
from services.utils import get_error_message
from services.utils import MgrException
from services.utils import pyunicore

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


def start_service(
    validated_data, initial_data, custom_headers, jhub_credential, logs_extra
):
    log.debug("Service start", extra=logs_extra)

    config = _config()

    try:
        ret = pyunicore.start_service(
            config,
            initial_data,
            validated_data,
            custom_headers,
            jhub_credential,
            logs_extra=logs_extra,
        )
        log.info(f"Service start finished - {ret}", extra=logs_extra)
        return ret
    except (MgrException, Exception) as e:
        log.warning(
            "Service start failed",
            extra=logs_extra,
            exc_info=True,
        )
        if e.__class__.__name__ == "MgrException":
            e_args = e.args
        else:
            user_error_msg = get_error_message(
                config,
                logs_extra,
                "services.utils.common.start_service",
                "Could not start service",
            )
            e_args = (user_error_msg, str(e))
        raise MgrException(*e_args)


def status_service(instance_dict, custom_headers, logs_extra):
    log.debug("Service status check", extra=logs_extra)

    config = _config()

    try:
        ret = pyunicore.status_service(
            config, instance_dict, custom_headers, logs_extra=logs_extra
        )
        log.info(f"Service status check finished - {ret}", extra=logs_extra)
        return ret
    except (MgrException, Exception) as e:
        log.warning("Service status check failed", extra=logs_extra, exc_info=True)
        if e.__class__.__name__ == "MgrException":
            e_args = e.args
        else:
            user_error_msg = get_error_message(
                config,
                logs_extra,
                "services.utils.common.status_service",
                "UNICORE error during status process.",
            )
            e_args = (user_error_msg, str(e))
        raise MgrException(*e_args)


def stop_service(instance_dict, custom_headers, logs_extra):
    log.debug("Service stop", extra=logs_extra)

    config = _config()

    try:
        pyunicore.stop_service(
            config, instance_dict, custom_headers, logs_extra, raise_exception=True
        )
        log.info("Service stop finished", extra=logs_extra)
    except (MgrException, Exception) as e:
        log.warning(
            "Service stop failed",
            extra=logs_extra,
            exc_info=True,
        )
        if e.__class__.__name__ == "MgrException":
            e_args = e.args
        else:
            user_error_msg = get_error_message(
                config,
                logs_extra,
                "services.utils.common.stop_service",
                "Could not stop service",
            )
            e_args = (user_error_msg, str(e))
        raise MgrException(*e_args)


def initial_data_to_logs_extra(servername, initial_data, custom_headers):
    # Remove secrets for logging
    logs_extra = copy.deepcopy(initial_data)
    if "access_token" in logs_extra.get("auth_state", {}).keys():
        logs_extra["auth_state"]["access_token"] = "***"
    logs_extra["env"]["JUPYTERHUB_API_TOKEN"] = "***"
    if "JPY_API_TOKEN" in logs_extra["env"]:  # deprecated in JupyterHub
        logs_extra["env"]["JPY_API_TOKEN"] = "***"
    logs_extra.update(copy.deepcopy(custom_headers))
    if "access-token" in logs_extra.keys():
        logs_extra["access-token"] = "***"
    if "uuidcode" not in logs_extra.keys():
        logs_extra["uuidcode"] = servername
    if "certs" in logs_extra.keys():
        logs_extra["certs"] = "***"
    return logs_extra


def instance_dict_and_custom_headers_to_logs_extra(instance_dict, custom_headers):
    # Remove secrets for logging
    logs_extra = copy.deepcopy(instance_dict)
    logs_extra.update(copy.deepcopy(custom_headers))
    if "start_date" in logs_extra.keys():
        if logs_extra["start_date"].__class__.__name__ == "datetime":
            logs_extra["start_date"] = logs_extra["start_date"].isoformat()
    if "_state" in logs_extra.keys():
        del logs_extra["_state"]
    if "access-token" in logs_extra.keys():
        logs_extra["access-token"] = "***"
    if "uuidcode" not in logs_extra.keys():
        logs_extra["uuidcode"] = uuid.uuid4().hex
    return logs_extra
