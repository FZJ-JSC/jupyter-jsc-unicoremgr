import copy
import html
import json
import logging
import os

import pyunicore.client as pyunicore
from jupyterjsc_unicoremgr.settings import LOGGER_NAME
from services.utils import get_download_delete
from services.utils import get_error_message
from services.utils import MgrException

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


def start_service(
    config, initial_data, instance_dict, custom_headers, jhub_credential, logs_extra
):
    log.debug("Start pyunicore", extra=logs_extra)
    job = None
    try:
        client = _get_client(
            config,
            instance_dict,
            custom_headers,
            logs_extra=logs_extra,
        )
        job_description = _get_job_description(
            config, jhub_credential, initial_data, logs_extra=logs_extra
        )
        job = client.new_job(job_description)
        resource_url = job.resource_url
        log.debug(
            f"Start pyunicore job - resource_url: {resource_url}", extra=logs_extra
        )
        return {"resource_url": resource_url}
    except (MgrException, Exception) as e:
        log.warning("Start pyunicore failed", extra=logs_extra, exc_info=True)
        # If an error occured during the start process, the UNICORE Job might
        # be running. If this is the case, we have to try to stop it.
        try:
            if job:
                job.abort()
        except:
            log.critical(
                "Could not abort previously started job",
                extra=logs_extra,
                exc_info=True,
            )
        if e.__class__.__name__ == "MgrException":
            e_args = e.args
        else:
            user_error_msg = get_error_message(
                config,
                logs_extra,
                "services.utils.pyunicore.start_job",
                "UNICORE error during start process.",
            )
            e_args = (user_error_msg, str(e))
        raise MgrException(*e_args)


def _jd_template(config, jhub_credential, initial_data):
    jhub_credential_mapped = config.get("credential_mapping", {}).get(
        jhub_credential, jhub_credential
    )
    mapped_system = (
        config.get("systems", {})
        .get("mapping", {})
        .get("system", {})
        .get(
            initial_data["user_options"]["system"],
            initial_data["user_options"]["system"],
        )
    )
    base_dir = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("base_directory", "/mnt/config/job_descriptions")
    )
    template_filename = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("template_filename", "job_description.json.template")
    )
    template_path = os.path.join(
        base_dir,
        jhub_credential_mapped,
        initial_data["user_options"]["service"],
        mapped_system,
        template_filename,
    )
    with open(template_path, "r") as f:
        template = json.load(f)
    return template


def _jd_add_initial_data_env(config, initial_data, jd, logs_extra):
    mapped_system = (
        config.get("systems", {})
        .get("mapping", {})
        .get("system", {})
        .get(
            initial_data["user_options"]["system"],
            initial_data["user_options"]["system"],
        )
    )
    environment_key = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("unicore_keywords", {})
        .get("environment_key", "Environment")
    )
    skip_environments = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("unicore_keywords", {})
        .get("skip_environments", ["JUPYTERHUB_API_TOKEN", "JPY_API_TOKEN"])
    )
    if environment_key not in jd:
        jd[environment_key] = {}
    for key, value in initial_data["env"].items():
        if key not in skip_environments:
            jd[environment_key][key] = str(value)
    if "certs" in initial_data.keys():
        certs_keyfile_name = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("certs", {})
            .get("keyfile_name", "service_cert.key")
        )
        certs_certfile_name = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("certs", {})
            .get("keyfile_name", "service_cert.crt")
        )
        certs_cafile_name = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("certs", {})
            .get("keyfile_name", "service_ca.crt")
        )
        jd[environment_key]["JUPYTERHUB_SSL_KEYFILE_DATA"] = str(certs_keyfile_name)
        jd[environment_key]["JUPYTERHUB_SSL_CERTFILE_DATA"] = str(certs_certfile_name)
        jd[environment_key]["JUPYTERHUB_SSL_CLIENT_CA_DATA"] = str(certs_cafile_name)

    return jd


def _jd_replace(config, initial_data, jd):
    jd_as_string = json.dumps(jd)
    mapped_system = (
        config.get("systems", {})
        .get("mapping", {})
        .get("system", {})
        .get(
            initial_data["user_options"]["system"],
            initial_data["user_options"]["system"],
        )
    )
    replace_indicators = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("replace_indicators", ["<", ">"])
    )
    for key, value in initial_data.get("user_options", {}).items():
        if type(value) == str:
            jd_as_string = jd_as_string.replace(
                f"{replace_indicators[0]}{key}{replace_indicators[1]}", value
            )
    for key, value in initial_data.get("env", {}).items():
        if type(value) == str:
            jd_as_string = jd_as_string.replace(
                f"{replace_indicators[0]}{key}{replace_indicators[1]}", value
            )
    return json.loads(jd_as_string)


def _jd_insert_job_type(config, initial_data, jd):
    mapped_system = (
        config.get("systems", {})
        .get("mapping", {})
        .get("system", {})
        .get(
            initial_data["user_options"]["system"],
            initial_data["user_options"]["system"],
        )
    )
    job_type_key = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("unicore_keywords", {})
        .get("type_key", "Job type")
    )
    if initial_data["user_options"]["partition"] in (
        config.get("systems", {})
        .get(initial_data["user_options"]["system"], {})
        .get("interactive_partitions", {})
        .keys()
    ):
        job_type_value = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("unicore_keywords", {})
            .get("interactive", {})
            .get("type_value", "interactive")
        )
        interactive_node_key = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("unicore_keywords", {})
            .get("interactive", {})
            .get("node_key", "Login node")
        )
        interactive_node_value = (
            config.get("systems", {})
            .get(initial_data["user_options"]["system"], {})
            .get("interactive_partitions", {})
            .get(
                initial_data["user_options"]["partition"],
                initial_data["user_options"]["partition"],
            )
        )
        jd[job_type_key] = job_type_value
        jd[interactive_node_key] = interactive_node_value
    else:
        normal_value = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("unicore_keywords", {})
            .get("normal", {})
            .get("type_value", "normal")
        )
        jd[job_type_key] = normal_value
        resources_key = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("unicore_keywords", {})
            .get("normal", {})
            .get("resources_key", "Resources")
        )
        queue_key = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("unicore_keywords", {})
            .get("normal", {})
            .get("queue_key", "Queue")
        )
        set_queue = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("unicore_keywords", {})
            .get("normal", {})
            .get("set_queue", True)
        )
        if resources_key not in jd:
            jd[resources_key] = {}
        if set_queue:
            jd[resources_key][queue_key] = initial_data["user_options"]["partition"]
        for key, new_key in (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("resource_mapping", {})
            .items()
        ):
            if key in initial_data["user_options"].keys():
                jd[resources_key][new_key] = initial_data["user_options"][key]
        # Add reservation if any given
        user_options_reservation_key = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("normal", {})
            .get("user_options_reservation_key", "reservation")
        )
        if user_options_reservation_key in initial_data["user_options"].keys():
            reservation_key = (
                config.get("systems", {})
                .get(mapped_system, {})
                .get("pyunicore", {})
                .get("job_description", {})
                .get("normal", {})
                .get("reservation_key", "Reservation")
            )
            jd[resources_key][reservation_key] = initial_data["user_options"][
                user_options_reservation_key
            ]
    return jd


def _jd_add_input_files(config, jhub_credential, initial_data, jd, logs_extra={}):
    jhub_credential_mapped = config.get("credential_mapping", {}).get(
        jhub_credential, jhub_credential
    )
    mapped_system = (
        config.get("systems", {})
        .get("mapping", {})
        .get("system", {})
        .get(
            initial_data["user_options"]["system"],
            initial_data["user_options"]["system"],
        )
    )
    base_dir = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("base_directory", "/mnt/config/job_descriptions")
    )
    input_dir_name = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("input", {})
        .get("directory_name", "input")
    )
    input_dir = os.path.join(
        base_dir,
        jhub_credential_mapped,
        initial_data["user_options"]["service"],
        mapped_system,
        input_dir_name,
    )
    skip_prefixs = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("input", {})
        .get("skip_prefixs", ["skip_"])
    )
    skip_suffixs = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("input", {})
        .get("skip_suffixs", [".swp"])
    )
    system = initial_data["user_options"]["system"]
    stage = os.environ.get("STAGE", "").lower()

    # We will skip files that are not meant for specific configurations 
    if stage:
        stages_to_skip = [
            f"{x}_"
            for x in config.get("systems", {})
            .get("mapping", {})
            .get("skip", {})
            .get("stage", [])
            if x != stage
        ]
        skip_prefixs.extend(stages_to_skip)

        # Same stage but different credential
        stages_credential_to_skip = [
            f"{stage}_{x}_"
            for x in config.get("systems", {})
            .get("mapping", {})
            .get("skip", {})
            .get("credential", [])
            if x != jhub_credential
        ]
        skip_prefixs.extend(stages_credential_to_skip)

        # Same stage but different system
        stages_system_to_skip = [
            f"{stage}_{x}_"
            for x in config.get("systems", {})
            .get("mapping", {})
            .get("skip", {})
            .get("system", [])
            if x != system
        ]
        skip_prefixs.extend(stages_system_to_skip)

        # Same stage and credential but different system
        stages_credential_system_to_skip = [
            f"{stage}_{x}_{system}_"
            for x in config.get("systems", {})
            .get("mapping", {})
            .get("skip", {})
            .get("credential", [])
            if x != jhub_credential
        ]
        skip_prefixs.extend(stages_credential_system_to_skip)

    # Same credential but different system
    credential_system_to_skip = [
        f"{jhub_credential}_{x}_"
        for x in config.get("systems", {})
        .get("mapping", {})
        .get("skip", {})
        .get("system", [])
        if x != system
    ]
    skip_prefixs.extend(credential_system_to_skip)

    credential_to_skip = [
        f"{x}_"
        for x in config.get("systems", {})
        .get("mapping", {})
        .get("skip", {})
        .get("credential", [])
        if x != jhub_credential
    ]
    skip_prefixs.extend(credential_to_skip)

    system_to_skip = [
        f"{x}_"
        for x in config.get("systems", {})
        .get("mapping", {})
        .get("skip", {})
        .get("system", [])
        if x != system
    ]
    skip_prefixs.extend(system_to_skip)
    replace_indicators = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("replace_indicators", ["<", ">"])
    )
    imports_from_value = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("job_description", {})
        .get("unicore_keywords", {})
        .get("imports_from_value", "inline://dummy")
    )
    input_files = os.listdir(input_dir)
    imports = []
    for filename in input_files:
        skip = False
        for prefix in skip_prefixs:
            if filename.startswith(prefix):
                skip = True
                break
        if skip:
            continue
        for suffix in skip_suffixs:
            if filename.endswith(suffix):
                skip = True
                break
        if skip:
            continue

        newname = filename
        if filename.startswith(f"{stage}_{jhub_credential}_{system}_"):
            newname = filename[
                len(stage) + 1 + len(jhub_credential) + 1 + len(system) + 1 :
            ]
        elif filename.startswith(f"{stage}_{jhub_credential}_"):
            newname = filename[len(stage) + 1 + len(jhub_credential) + 1 :]
        elif filename.startswith(f"{stage}_{system}_"):
            newname = filename[len(stage) + 1 + len(system) + 1 :]
        elif filename.startswith(f"{jhub_credential}_{system}_"):
            newname = filename[len(jhub_credential) + 1 + len(system) + 1 :]
        elif filename.startswith(f"{stage}_"):
            newname = filename[len(stage) + 1 :]
        elif filename.startswith(f"{jhub_credential}_"):
            newname = filename[len(jhub_credential) + 1 :]
        elif filename.startswith(f"{system}_"):
            newname = filename[len(system) + 1 :]
        with open(os.path.join(input_dir, filename), "r") as f:
            file_data = f.read()
        for key, value in initial_data.get("user_options", {}).items():
            if type(value) == str:
                file_data = file_data.replace(
                    f"{replace_indicators[0]}{key}{replace_indicators[1]}", value
                )
        for key, value in initial_data.get("env", {}).items():
            if type(value) == str:
                file_data = file_data.replace(
                    f"{replace_indicators[0]}{key}{replace_indicators[1]}", value
                )
        # We will replace keywords with configured values.
        # We start with the most specific replacements and follow up with the least specific ones
        if stage:
            # Replace values specified for stage+credential+system
            for key, value in (
                config.get("systems", {})
                .get("mapping", {})
                .get("replace", {})
                .get("stage_credential_system", {})
                .get(stage, {})
                .get(jhub_credential, {})
                .get(initial_data["user_options"]["system"], {})
                .items()
            ):
                file_data = file_data.replace(
                    f"{replace_indicators[0]}{key}{replace_indicators[1]}",
                    value,
                )

            # Replace values specified for stage+credential
            for key, value in (
                config.get("systems", {})
                .get("mapping", {})
                .get("replace", {})
                .get("stage_credential", {})
                .get(stage, {})
                .get(jhub_credential, {})
                .items()
            ):
                file_data = file_data.replace(
                    f"{replace_indicators[0]}{key}{replace_indicators[1]}",
                    value,
                )
            
            # Replace values specified for stage+system
            for key, value in (
                config.get("systems", {})
                .get("mapping", {})
                .get("replace", {})
                .get("stage_system", {})
                .get(stage, {})
                .get(initial_data["user_options"]["system"], {})
                .items()
            ):
                file_data = file_data.replace(
                    f"{replace_indicators[0]}{key}{replace_indicators[1]}",
                    value,
                )
            
            # Replace values specified for stage
            for key, value in (
                config.get("systems", {})
                .get("mapping", {})
                .get("replace", {})
                .get("stage", {})
                .get(stage, {})
                .items()
            ):
                file_data = file_data.replace(
                    f"{replace_indicators[0]}{key}{replace_indicators[1]}",
                    value,
                )

        # Replace values specified for credential+system
        for key, value in (
            config.get("systems", {})
            .get("mapping", {})
            .get("replace", {})
            .get("credential_system", {})
            .get(jhub_credential, {})
            .get(initial_data["user_options"]["system"], {})
            .items()
        ):
            file_data = file_data.replace(
                f"{replace_indicators[0]}{key}{replace_indicators[1]}",
                value,
            )

        # Replace values specified for credential
        for key, value in (
            config.get("systems", {})
            .get("mapping", {})
            .get("replace", {})
            .get("credential", {})
            .get(jhub_credential, {})
            .items()
        ):
            file_data = file_data.replace(
                f"{replace_indicators[0]}{key}{replace_indicators[1]}",
                value,
            )
        
        # Replace values specified for system
        for key, value in (
            config.get("systems", {})
            .get("mapping", {})
            .get("replace", {})
            .get("system", {})
            .get(initial_data["user_options"]["system"], {})
            .items()
        ):
            file_data = file_data.replace(
                f"{replace_indicators[0]}{key}{replace_indicators[1]}",
                value,
            )
        

        # Hooks can be used to change file for specific user_options
        # Example:
        # "hooks": {
        #   "load_project_specific_kernel": {
        #       "project": ["hai_ds_isa", "training2223"]
        #   }
        # },
        #
        # This will replace <hook_load_project_specific_kernel> in all files with 1
        # if initial_data["user_options"]["project"] is in ["hai_ds_isa", "training2223"].
        # For all other projects it's replaced with 0
        #
        # You can combine multiple user_options. They are connected with an AND operator, so
        # the user_options must be part of all configured lists.
        for hook_name, hook_infos in (
            config.get("systems", {})
            .get(initial_data["user_options"]["system"], {})
            .get("hooks", {})
            .items()
        ):
            log.trace(f"Job Description: check hook {hook_name}", extra=logs_extra)
            replace_string = "1"
            for user_options_key, user_options_values in hook_infos.items():
                log.trace(
                    f"Job Description - {hook_name} - {user_options_key}",
                    extra=logs_extra,
                )
                key_is_in = (
                    initial_data["user_options"].get(user_options_key, "")
                    in user_options_values
                )
                log.trace(
                    f"Job Description - {hook_name} - {initial_data['user_options'].get(user_options_key, '')} in {user_options_values} : {key_is_in}",
                    extra=logs_extra,
                )
                if not key_is_in:
                    replace_string = "0"
                    break
            log.trace(
                f"Job Description: hook {hook_name} replace with: {replace_string}",
                extra=logs_extra,
            )
            file_data = file_data.replace(
                f"{replace_indicators[0]}hook_{hook_name}{replace_indicators[1]}",
                replace_string,
            )
        imports.append(
            {"From": imports_from_value, "To": newname, "Data": file_data.strip()}
        )
    if "certs" in initial_data.keys():
        certs_keyfile_name = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("certs", {})
            .get("keyfile_name", "service_cert.key")
        )
        certs_certfile_name = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("certs", {})
            .get("keyfile_name", "service_cert.crt")
        )
        certs_cafile_name = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("certs", {})
            .get("keyfile_name", "service_ca.crt")
        )
        imports.append(
            {
                "From": imports_from_value,
                "To": certs_keyfile_name,
                "Data": initial_data["certs"]["keyfile"],
            }
        )
        imports.append(
            {
                "From": imports_from_value,
                "To": certs_certfile_name,
                "Data": initial_data["certs"]["certfile"],
            }
        )
        imports.append(
            {
                "From": imports_from_value,
                "To": certs_cafile_name,
                "Data": initial_data["certs"]["cafile"],
            }
        )
    if imports:
        imports_key = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("pyunicore", {})
            .get("job_description", {})
            .get("unicore_keywords", {})
            .get("imports_key", "Imports")
        )
        jd[imports_key] = imports
    return jd


def _get_job_description(config, jhub_credential, initial_data, logs_extra):
    log.trace("Create job_description", extra=logs_extra)
    jd = _jd_template(config, jhub_credential, initial_data)
    jd = _jd_add_initial_data_env(config, initial_data, jd, logs_extra)
    jd = _jd_replace(config, initial_data, jd)
    jd = _jd_insert_job_type(config, initial_data, jd)
    jd = _jd_add_input_files(
        config, jhub_credential, initial_data, jd, logs_extra=logs_extra
    )
    jd_logs_extra = copy.deepcopy(logs_extra)
    jd_logs_extra.update({"jobs_description": jd})
    log.trace("Create job description... done", extra=jd_logs_extra)
    return jd


def _get_job(config, instance_dict, custom_headers, logs_extra):
    transport = _get_transport(config, instance_dict, custom_headers, logs_extra)
    job = pyunicore.Job(transport, instance_dict["resource_url"])
    return job


def stop_service(
    config, instance_dict, custom_headers, logs_extra, raise_exception=True
):
    log.debug("Service stop pyunicore", extra=logs_extra)

    mapped_system = (
        config.get("systems", {})
        .get("mapping", {})
        .get("system", {})
        .get(
            instance_dict["user_options"]["system"],
            instance_dict["user_options"]["system"],
        )
    )

    download, delete = get_download_delete(
        config, instance_dict, mapped_system, logs_extra
    )
    try:
        log.debug(
            f"Stop pyunicore Service - Get Job: {instance_dict['resource_url']} ...",
            extra=logs_extra,
        )
        job = _get_job(config, instance_dict, custom_headers, logs_extra)
        log.debug("Stop pyunicore Service - Get Job: ... done", extra=logs_extra)
        job.abort()
        log.debug("Stop pyunicore Service - Job aborted", extra=logs_extra)

        if download:
            log.debug("Stop pyunicore Service - Download Job file", extra=logs_extra)
            _download_service(
                instance_dict["id"],
                instance_dict["servername"],
                config,
                job,
                mapped_system,
                logs_extra=logs_extra,
            )

        if delete:
            log.debug("Stop pyunicore Service - Delete job", extra=logs_extra)
            job.delete()

    except (MgrException, Exception) as e:
        log.warning("pyunicore - Service stop failed", exc_info=True, extra=logs_extra)
        if e.__class__.__name__ == "MgrException":
            e_args = e.args
        else:
            user_error_msg = get_error_message(
                config,
                logs_extra,
                "services.utils.pyunicore.stop_service",
                "Could not stop service",
            )
            e_args = (user_error_msg, str(e))
        log.warning(
            f"pyunicore - Service stop error message {e_args}", extra=logs_extra
        )
        if raise_exception:
            raise MgrException(*e_args)


def _create_dir(dir, logs_extra={}):
    log.trace(f"Create directory: {dir}", extra=logs_extra)
    if os.path.exists(dir):
        log.critical(f"Create directory - {dir} already exists.")
    os.makedirs(dir, exist_ok=True)


def _download_job_files(storage, destination_base_dir, base="/", logs_extra={}):
    destination_base_dir_rstrip = destination_base_dir.rstrip("/")
    destination_dir = f"{destination_base_dir_rstrip}{base}".rstrip("/")
    _create_dir(destination_dir, logs_extra=logs_extra)

    dict_of_paths = storage.listdir(base)
    for name, path in dict_of_paths.items():
        file_destination = f"{destination_base_dir_rstrip}/{name}"
        if path.isfile():
            log.trace(f"Download Service - download: {name}", extra=logs_extra)
            path.download(file_destination)
        elif path.isdir():
            _download_job_files(
                storage, destination_base_dir, f"/{name}", logs_extra=logs_extra
            )


def _download_service(drf_id, servername, config, job, system, logs_extra={}):
    destination_dir = (
        config.get("systems", {})
        .get(system, {})
        .get("pyunicore", {})
        .get("job_archive", "/tmp")
    )
    destination = f"{destination_dir.rstrip('/')}/{drf_id}_{servername}_{job.job_id}"
    storage = job.working_dir
    log.debug(f"Download Service files - {storage} to {destination}", extra=logs_extra)
    _download_job_files(storage, destination, "/", logs_extra=logs_extra)


def _get_file_output(job, file, max_bytes):
    try:
        file_path = job.working_dir.stat(file)
        file_size = file_path.properties["size"]
        if file_size == 0:
            return f"{file} is empty"
        offset = max(0, file_size - max_bytes)
        s = file_path.raw(offset=offset)
        ret = s.data.decode()
        return ret
    except Exception as e:
        log.warning("Could not receive file info", exc_info=True)
        return f"{file} not available."


def _prettify_error_logs(log_list, join_s, lines, summary):
    if type(log_list) == str:
        log_list = log_list.split("\n")
    if type(log_list) == list:
        if lines > 0:
            log_list_short = log_list[-lines:]
        if lines < len(log_list):
            log_list_short.insert(0, "...")
        log_list_short_escaped = list(map(lambda x: html.escape(x), log_list_short))
        logs_s = join_s.join(log_list_short_escaped)
    else:
        logs_s = log_list.split()
        logs_s = html.escape(logs_s)
    return f"<details><summary>{summary}</summary>{logs_s}</details>"


def status_service(config, instance_dict, custom_headers, logs_extra):
    log.trace("Get Service status", extra=logs_extra)
    job = _get_job(
        config,
        instance_dict,
        custom_headers,
        logs_extra=logs_extra,
    )

    mapped_system = (
        config.get("systems", {})
        .get("mapping", {})
        .get("system", {})
        .get(
            instance_dict["user_options"]["system"],
            instance_dict["user_options"]["system"],
        )
    )

    if custom_headers.get("DOWNLOAD", "false").lower() == "true":
        _download_service(
            instance_dict["id"],
            instance_dict["servername"],
            config,
            job,
            mapped_system,
            logs_extra=logs_extra,
        )
    running = job.is_running()
    log.trace(f"Get Service status - running: {running}", extra=logs_extra)
    if not running:
        # Get useful output for user
        unicore_detailed_error_join = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("detailed_error_join", "")
        )
        unicore_logs_lines = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_logs", {})
            .get("lines", 3)
        )
        unicore_logs_join = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_logs", {})
            .get("join", "<br>")
        )
        unicore_logs_summary = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_logs", {})
            .get("summary", "&nbsp&nbsp&nbsp&nbspUNICORE logs:")
        )

        unicore_stdout_lines = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_stdout", {})
            .get("lines", 5)
        )
        unicore_stdout_join = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_stdout", {})
            .get("join", "<br>")
        )
        unicore_stdout_max_bytes = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_stdout", {})
            .get("max_bytes", 4096)
        )
        unicore_stdout_summary = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_stdout", {})
            .get("summary", "&nbsp&nbsp&nbsp&nbspJob stdout:")
        )

        unicore_stderr_lines = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_stderr", {})
            .get("lines", 5)
        )
        unicore_stderr_join = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_stderr", {})
            .get("join", "<br>")
        )
        unicore_stderr_max_bytes = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_stderr", {})
            .get("max_bytes", 4096)
        )
        unicore_stderr_summary = (
            config.get("systems", {})
            .get(mapped_system, {})
            .get("status_information", {})
            .get("unicore_stderr", {})
            .get("summary", "&nbsp&nbsp&nbsp&nbspJob stderr:")
        )

        unicore_exit_code = job.properties.get("exitCode", "unknown exitCode")
        error_msg = f"UNICORE Job stopped with exitCode: {unicore_exit_code}"
        unicore_status_message = job.properties.get(
            "statusMessage", "unknown statusMessage"
        )

        unicore_logs = job.properties.get("log", [])
        unicore_logs_details = _prettify_error_logs(
            unicore_logs, unicore_logs_join, unicore_logs_lines, unicore_logs_summary
        )

        unicore_stdout = _get_file_output(job, "stdout", unicore_stdout_max_bytes)
        unicore_stderr = _get_file_output(job, "stderr", unicore_stderr_max_bytes)
        unicore_stdout_details = _prettify_error_logs(
            unicore_stdout,
            unicore_stdout_join,
            unicore_stdout_lines,
            unicore_stdout_summary,
        )
        unicore_stderr_details = _prettify_error_logs(
            unicore_stderr,
            unicore_stderr_join,
            unicore_stderr_lines,
            unicore_stderr_summary,
        )
        detailed_error_list = [
            unicore_status_message,
            unicore_logs_details,
            unicore_stdout_details,
            unicore_stderr_details,
        ]
        detailed_error = unicore_detailed_error_join.join(detailed_error_list)
        logs_extra["error_msg"] = error_msg
        logs_extra["detailed_error"] = detailed_error
        log.debug("Information shown to user", logs_extra)
        return {
            "running": running,
            "details": {
                "error": error_msg,
                "detailed_error": detailed_error,
            },
        }
    else:
        return {"running": running}


def _get_transport(
    config,
    instance_dict,
    custom_headers,
    logs_extra={},
):
    log.trace("pyunicore - get transport", extra=logs_extra)
    credential = custom_headers["access-token"]
    mapped_system = (
        config.get("systems", {})
        .get("mapping", {})
        .get("system", {})
        .get(
            instance_dict["user_options"]["system"],
            instance_dict["user_options"]["system"],
        )
    )
    oidc = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("transport", {})
        .get("oidc", True)
    )
    certificate_path = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("transport", {})
        .get("certificate_path", False)
    )
    timeout = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("transport", {})
        .get("timeout", 120)
    )
    set_preferences = (
        config.get("systems", {})
        .get(mapped_system, {})
        .get("pyunicore", {})
        .get("transport", {})
        .get("set_preferences", True)
    )
    log.trace(
        f"pyunicore - oidc={oidc} - cert={certificate_path} - timeout={timeout} - set_preferences={set_preferences}",
        extra=logs_extra,
    )
    try:
        transport = pyunicore.Transport(
            credential=credential,
            oidc=oidc,
            verify=certificate_path,
            timeout=timeout,
        )
        log.trace("pyunicore - received transport object", extra=logs_extra)
        if set_preferences:
            transport.preferences = f"uid:{instance_dict['user_options']['account']},group:{instance_dict['user_options']['project']}"
    except Exception as e:
        error_message = get_error_message(
            config,
            logs_extra,
            "services.utils.pyunicore._get_transport",
            "UNICORE error.",
        )
        raise MgrException(error_message, str(e))
    return transport


def _get_client(config, instance_dict, custom_headers, logs_extra={}):
    site_url = (
        config.get("systems", {})
        .get(instance_dict["user_options"]["system"], {})
        .get("site_url", "https://localhost:8080/DEMO-SITE/rest/core")
    )
    transport = _get_transport(config, instance_dict, custom_headers, logs_extra)
    try:
        client = pyunicore.Client(transport, site_url)
        log.trace("pyunicore - retrieved client object", extra=logs_extra)
    except Exception as e:
        error_message = get_error_message(
            config,
            logs_extra,
            "services.utils.pyunicore._get_client",
            "UNICORE error.",
        )
        raise MgrException(error_message, str(e))
    return client
