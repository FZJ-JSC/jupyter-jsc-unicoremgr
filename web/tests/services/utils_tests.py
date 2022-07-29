import copy
import json
import uuid
from unittest import mock

from rest_framework.test import APITestCase
from services.models import ServicesModel
from services.utils import common
from services.utils import pyunicore
from tests.services.mocks import MockClient
from tests.services.mocks import mocked_exception
from tests.services.mocks import mocked_new_job
from tests.services.mocks import mocked_pass
from tests.services.mocks import mocked_pyunicore_client_init
from tests.services.mocks import mocked_pyunicore_job_init
from tests.services.mocks import mocked_pyunicore_transport_init
from tests.services.mocks import MockJob
from tests.user_credentials import mocked_requests_post_running

from .mocks import config_mock


class JobDescriptionTests(APITestCase):
    jhub_credential = "authorized"
    config = {
        "systems": {
            "mapping": {"system": {"DEMO-SITE": "default_system"}},
            "DEMO-SITE": {
                "site_url": "https://unicore-test.svc:9112/DEMO-SITE/rest/core",
                "hooks": {
                    "load_project_specific_kernel": {
                        "project": ["demoproject2"],
                        "partition": ["LoginNode"],
                    }
                },
                "interactive_partitions": {"LoginNode": "localhost"},
            },
            "default_system": {
                "pyunicore": {
                    "job_archive": "/tmp/job-archive",
                    "transport": {
                        "certificate_path": False,
                        "oidc": False,
                        "timeout": 5,
                        "set_preferences": False,
                    },
                    "cleanup": {
                        "enabled": True,
                        "tags": ["Jupyter-JSC"],
                        "max_per_start": 2,
                    },
                    "job_description": {
                        "base_directory": "web/tests/config/job_descriptions",
                        "template_filename": "job_description.json.template",
                        "replace_indicators": ["<", ">"],
                        "input": {
                            "directory_name": "input",
                            "skip_prefixs": ["skip_"],
                            "skip_suffixs": [".swp"],
                        },
                        "input_directory_name": "input",
                        "resource_mapping": {
                            "resource_nodes": "Nodes",
                            "resource_Runtime": "Runtime",
                            "resource_gpus": "GPUs",
                        },
                        "unicore_keywords": {
                            "type_key": "Job type",
                            "interactive": {
                                "type_value": "interactive",
                                "node_key": "Login node",
                            },
                            "normal": {
                                "type_value": "normal",
                                "resources_key": "Resources",
                                "queue_key": "Queue",
                                "set_queue": True,
                            },
                            "imports_key": "Imports",
                            "imports_from_value": "inline://dummy",
                            "environment_key": "Environment",
                            "skip_environments": [
                                "JUPYTERHUB_API_TOKEN",
                                "JPY_API_TOKEN",
                            ],
                        },
                    },
                },
            },
        },
        "credential_mapping": {"authorized": "default_credential"},
        "vos": {},
        "error_messages": {},
    }

    request_data_simple = {
        "user_options": {
            "system": "DEMO-SITE",
            "service": "JupyterLab/simple",
            "account": "account",
            "project": "project",
            "vo": "myvo",
        }
    }

    def test__jd_template(self):
        jd_template = pyunicore._jd_template(
            self.config, self.jhub_credential, self.request_data_simple
        )
        with open(
            "web/tests/config/job_descriptions/default_credential/JupyterLab/simple/default_system/job_description.json.template",
            "r",
        ) as f:
            jd_template_manual = json.load(f)
        self.assertEqual(jd_template, jd_template_manual)

    def test__jd_replace(self):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace"
        data["env"] = {"env_REPLACE_ME": "5"}
        jd_template = pyunicore._jd_template(self.config, self.jhub_credential, data)
        jd = pyunicore._jd_replace(self.config, data, jd_template)
        self.assertEqual(jd["Arguments"], ["Hello World on DEMO-SITE - 5"])

    def test__jd_replace_custom_indicators(self):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace-custom-indicators"
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["job_description"][
            "replace_indicators"
        ] = ["<??", "??>"]
        jd_template = pyunicore._jd_template(config, self.jhub_credential, data)
        jd = pyunicore._jd_replace(config, data, jd_template)
        self.assertEqual(jd["Arguments"], ["Hello World on DEMO-SITE"])

    def test__jd_insert_job_type_interactive(self):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["partition"] = "LoginNode"
        jd_template = pyunicore._jd_template(self.config, self.jhub_credential, data)
        jd = pyunicore._jd_insert_job_type(self.config, data, jd_template)
        job_type_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["type_key"]
        job_type_value = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["interactive"]["type_value"]
        interactive_node_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["interactive"]["node_key"]
        self.assertEqual(jd[job_type_key], job_type_value)
        self.assertEqual(
            jd[interactive_node_key],
            self.config["systems"]["DEMO-SITE"]["interactive_partitions"][
                data["user_options"]["partition"]
            ],
        )

    def test__jd_insert_job_type_normal(self):
        data = copy.deepcopy(self.request_data_simple)
        jhub_resource_gpus_key = "resource_gpus"
        jhub_resource_gpus_value = "4"
        data["user_options"]["partition"] = "devel"
        data["user_options"][jhub_resource_gpus_key] = jhub_resource_gpus_value
        jd_template = pyunicore._jd_template(self.config, self.jhub_credential, data)
        jd = pyunicore._jd_insert_job_type(self.config, data, jd_template)
        job_type_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["type_key"]
        job_type_value = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["normal"]["type_value"]
        resources_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["normal"]["resources_key"]
        queue_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["normal"]["queue_key"]
        unicore_resource_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["resource_mapping"][jhub_resource_gpus_key]
        self.assertEqual(jd[job_type_key], job_type_value)
        self.assertEqual(
            jd[resources_key][queue_key], data["user_options"]["partition"]
        )
        self.assertEqual(
            jd[resources_key][unicore_resource_key], jhub_resource_gpus_value
        )

    def test__jd_insert_job_type_normal_set_queue_false(self):
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["job_description"][
            "unicore_keywords"
        ]["normal"]["set_queue"] = False
        data = copy.deepcopy(self.request_data_simple)
        jhub_resource_gpus_key = "resource_gpus"
        jhub_resource_gpus_value = "4"
        data["user_options"]["partition"] = "devel"
        data["user_options"][jhub_resource_gpus_key] = jhub_resource_gpus_value
        jd_template = pyunicore._jd_template(config, self.jhub_credential, data)
        jd = pyunicore._jd_insert_job_type(config, data, jd_template)
        job_type_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["type_key"]
        job_type_value = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["normal"]["type_value"]
        resources_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["normal"]["resources_key"]
        queue_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["unicore_keywords"]["normal"]["queue_key"]
        unicore_resource_key = self.config["systems"]["default_system"]["pyunicore"][
            "job_description"
        ]["resource_mapping"][jhub_resource_gpus_key]
        self.assertEqual(jd[job_type_key], job_type_value)
        self.assertNotIn(queue_key, jd[resources_key].keys())

    def test__jd_add_input_files_replace_hooks_1(self):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace-custom-indicators"
        data["user_options"]["project"] = "myproject"
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["job_description"][
            "replace_indicators"
        ] = ["<??", "??>"]
        config["systems"]["DEMO-SITE"]["hooks"]["project_kernel"] = {
            "project": "myproject"
        }
        jd_template = pyunicore._jd_template(config, self.jhub_credential, data)
        jd = pyunicore._jd_add_input_files(
            config, self.jhub_credential, data, jd_template
        )
        imports = jd[
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_key"]
        ]
        self.assertEqual(len(imports), 1)
        self.assertEqual(
            imports[0]["From"],
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_from_value"],
        )
        self.assertEqual(imports[0]["To"], "start.sh")
        self.assertIn('echo "Replace project_kernel: 1"', imports[0]["Data"])

    def test__jd_add_input_files_replace_hooks_0(self):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace-custom-indicators"
        data["user_options"]["project"] = "myproject1"
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["job_description"][
            "replace_indicators"
        ] = ["<??", "??>"]
        config["systems"]["DEMO-SITE"]["hooks"]["project_kernel"] = {
            "project": "myproject"
        }
        jd_template = pyunicore._jd_template(config, self.jhub_credential, data)
        jd = pyunicore._jd_add_input_files(
            config, self.jhub_credential, data, jd_template
        )
        imports = jd[
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_key"]
        ]
        self.assertEqual(len(imports), 1)
        self.assertEqual(
            imports[0]["From"],
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_from_value"],
        )
        self.assertEqual(imports[0]["To"], "start.sh")
        self.assertIn('echo "Replace project_kernel: 0"', imports[0]["Data"])

    def test__jd_add_input_files_replace_user_options(self):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace-custom-indicators"
        data["user_options"]["project"] = "myproject1"
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["job_description"][
            "replace_indicators"
        ] = ["<??", "??>"]
        config["systems"]["DEMO-SITE"]["hooks"]["project_kernel"] = {
            "project": "myproject"
        }
        jd_template = pyunicore._jd_template(config, self.jhub_credential, data)
        jd = pyunicore._jd_add_input_files(
            config, self.jhub_credential, data, jd_template
        )
        imports = jd[
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_key"]
        ]
        self.assertEqual(len(imports), 1)
        self.assertEqual(
            imports[0]["From"],
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_from_value"],
        )
        self.assertEqual(imports[0]["To"], "start.sh")
        self.assertIn(
            f"echo \"Replace user_options system: {data['user_options']['system']}\"",
            imports[0]["Data"],
        )

    def test__jd_add_input_files_replace_env(self):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace-custom-indicators"
        data["env"] = {"JUPYTERHUB_USER_ID": "1"}
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["job_description"][
            "replace_indicators"
        ] = ["<??", "??>"]
        config["systems"]["DEMO-SITE"]["hooks"]["project_kernel"] = {
            "project": "myproject"
        }
        jd_template = pyunicore._jd_template(config, self.jhub_credential, data)
        jd = pyunicore._jd_add_input_files(
            config, self.jhub_credential, data, jd_template
        )
        imports = jd[
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_key"]
        ]
        self.assertEqual(len(imports), 1)
        self.assertEqual(
            imports[0]["From"],
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_from_value"],
        )
        self.assertEqual(imports[0]["To"], "start.sh")
        self.assertIn('echo "Replace env JUPYTERHUB_USER_ID: 1"', imports[0]["Data"])

    @mock.patch(
        "requests.post",
        side_effect=mocked_requests_post_running,
    )
    def test_get_job_description(self, mocked_requests):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace-custom-indicators"
        data["user_options"]["partition"] = "devel"
        data["env"] = {"JUPYTERHUB_USER_ID": "1"}
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["job_description"][
            "replace_indicators"
        ] = ["<??", "??>"]
        config["systems"]["DEMO-SITE"]["hooks"]["project_kernel"] = {
            "project": "myproject"
        }
        jd = pyunicore._get_job_description(config, self.jhub_credential, data, {})
        imports = jd[
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_key"]
        ]
        self.assertEqual(len(imports), 1)
        self.assertEqual(
            imports[0]["From"],
            config["systems"]["default_system"]["pyunicore"]["job_description"][
                "unicore_keywords"
            ]["imports_from_value"],
        )
        self.assertEqual(imports[0]["To"], "start.sh")
        self.assertIn('echo "Replace env JUPYTERHUB_USER_ID: 1"', imports[0]["Data"])

    @mock.patch(
        "requests.post",
        side_effect=mocked_requests_post_running,
    )
    def test_get_job_description_minimal_config(self, mocked_requests):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace"
        data["user_options"]["partition"] = "devel"
        data["env"] = {"JUPYTERHUB_USER_ID": "1"}
        config = {
            "systems": {
                "mapping": {"system": {"DEMO-SITE": "default_system"}},
                "default_system": {
                    "pyunicore": {
                        "job_description": {
                            "base_directory": "web/tests/config/job_descriptions"
                        }
                    },
                },
            },
            "credential_mapping": {"authorized": "default_credential"},
        }
        jd = pyunicore._get_job_description(config, self.jhub_credential, data, {})
        imports = jd["Imports"]
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0]["From"], "inline://dummy")
        self.assertEqual(imports[0]["To"], "start.sh")
        self.assertIn('echo "Replace env JUPYTERHUB_USER_ID: 1"', imports[0]["Data"])

    @mock.patch(
        "requests.post",
        side_effect=mocked_requests_post_running,
    )
    def test_get_job_description_multiple_keys_replace(self, mocked_requests):
        access_token = "secret"
        simple_request_data = {
            "user_options": {
                "vo": "myvo",
                "system": "DEMO-SITE",
                "service": "JupyterLab/simple-multiple-keys",
                "project": "demoproject",
                "partition": "LoginNode",
                "account": "demouser",
            },
            "auth_state": {"access_token": access_token},
            "env": {
                "JUPYTERHUB_USER_ID": 17,
                "JUPYTERHUB_API_TOKEN": "secret",
                "JUPYTERHUB_STATUS_URL": "none",
            },
        }
        config = {
            "systems": {
                "mapping": {"system": {"DEMO-SITE": "default_system"}},
                "DEMO-SITE": {
                    "hooks": {
                        "load_project_specific_kernel": {
                            "project": ["demoproject"],
                            "partition": ["LoginNode"],
                        }
                    },
                },
                "default_system": {
                    "pyunicore": {
                        "job_description": {
                            "base_directory": "web/tests/config/job_descriptions"
                        }
                    },
                },
            },
            "credential_mapping": {"authorized": "default_credential"},
        }
        jd = pyunicore._get_job_description(
            config, self.jhub_credential, simple_request_data, {}
        )
        imports = jd["Imports"]
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0]["From"], "inline://dummy")
        self.assertEqual(imports[0]["To"], "start.sh")
        self.assertIn('echo "Load hook: 1"', imports[0]["Data"])


global_tmp_jobs = []


class PyUnicoreTests(JobDescriptionTests):
    def get_request_data(self):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["account"] = "demouser"
        data["user_options"]["project"] = "demoproject"
        data["user_options"]["service"] = "JupyterLab/simple-replace"
        data["user_options"]["partition"] = "devel"
        data["env"] = {"JUPYTERHUB_USER_ID": "1"}
        return data

    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    def test__get_transport(self, mocked):
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["transport"] = {
            "set_preferences": False
        }
        data = self.get_request_data()
        data["auth_state"] = {"access_token": "123"}
        instance_dict = {"user_options": data["user_options"]}
        custom_headers = {"access-token": data["auth_state"]["access_token"]}
        transport = pyunicore._get_transport(config, instance_dict, custom_headers, {})
        self.assertTrue(mocked.called)
        self.assertIsNone(transport.preferences)

    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    def test__get_transport_set_preferences(self, mocked):
        data = self.get_request_data()
        data["auth_state"] = {"access_token": "123"}
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["transport"][
            "set_preferences"
        ] = True
        instance_dict = {"user_options": data["user_options"]}
        custom_headers = {"access-token": data["auth_state"]["access_token"]}
        transport = pyunicore._get_transport(config, instance_dict, custom_headers, {})
        self.assertTrue(mocked.called)
        self.assertEqual(
            transport.preferences,
            f"uid:{data['user_options']['account']},group:{data['user_options']['project']}",
        )

    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    def test__get_client(self, mocked_client, mocked_transport):
        data = copy.deepcopy(self.get_request_data())
        data["auth_state"] = {"access_token": "123"}

        instance_dict = {"user_options": data["user_options"]}
        custom_headers = {"access-token": data["auth_state"]["access_token"]}
        client = pyunicore._get_client(self.config, instance_dict, custom_headers, {})
        self.assertTrue(mocked_transport.called)
        self.assertTrue(mocked_client.called)
        self.assertEqual(client.__class__.__name__, "MockClient")

    def setup_random_db_entries(
        self, request_data, no_of_entries=1, add_to_db=True, tags=[]
    ):
        global global_tmp_jobs
        for i in range(0, no_of_entries):
            model_data = {
                "servername": uuid.uuid4().hex,
                "user_options": request_data["user_options"],
                "jhub_user_id": request_data["env"]["JUPYTERHUB_USER_ID"],
                "resource_url": f"https://localhost:8080/DEMO-SITE/rest/core/{uuid.uuid4().hex}",
            }
            global_tmp_jobs.append(MockJob(None, model_data["resource_url"], tags=tags))
            if add_to_db:
                ServicesModel(**model_data).save()

    def global_tmp_jobs_func(*args, **kwargs):
        global global_tmp_jobs
        ret = [x for x in global_tmp_jobs if x.tags == kwargs.get("tags", [])]
        return ret

    @mock.patch(
        "requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        "services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        "services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    def test__pyunicore_start_job(
        self, mocked_transport, mocked_client, mocked_requests
    ):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace-custom-indicators"
        data["user_options"]["partition"] = "devel"
        data["user_options"]["account"] = "account"
        data["user_options"]["project"] = "project"
        data["auth_state"] = {"access_token": "secret"}
        data["env"] = {"JUPYTERHUB_USER_ID": "1"}
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["job_description"][
            "replace_indicators"
        ] = ["<??", "??>"]
        config["systems"]["DEMO-SITE"]["hooks"]["project_kernel"] = {
            "project": "myproject"
        }
        instance_dict = {
            "user_options": data["user_options"],
            "servername": "random_uuid",
        }
        custom_headers = {"access-token": data["auth_state"]["access_token"]}

        result = pyunicore.start_service(
            config, data, instance_dict, custom_headers, self.jhub_credential, {}
        )
        resource_url = result["resource_url"]

        site_url = config["systems"]["DEMO-SITE"]["site_url"]
        self.assertTrue(resource_url.startswith(site_url))
        self.assertEqual(len(resource_url), len(site_url) + 1 + 32)  # / + 32uuidChars

    @mock.patch(
        "requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        "services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        "services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="tests.services.mocks.MockClient.new_job", side_effect=mocked_new_job
    )
    def test__pyunicore_start_job_call_new_job_once(
        self, mocked_new_job, mocked_transport, mocked_client, mocked_requests
    ):
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["service"] = "JupyterLab/simple-replace-custom-indicators"
        data["user_options"]["partition"] = "devel"
        data["user_options"]["account"] = "account"
        data["user_options"]["project"] = "project"
        data["auth_state"] = {"access_token": "secret"}
        data["env"] = {"JUPYTERHUB_USER_ID": "1"}
        config = copy.deepcopy(self.config)
        config["systems"]["default_system"]["pyunicore"]["job_description"][
            "replace_indicators"
        ] = ["<??", "??>"]
        config["systems"]["DEMO-SITE"]["hooks"]["project_kernel"] = {
            "project": "myproject"
        }

        instance_dict = {
            "user_options": data["user_options"],
            "servername": "random_uuid",
        }
        custom_headers = {"access-token": data["auth_state"]["access_token"]}

        result = pyunicore.start_service(
            config, data, instance_dict, custom_headers, self.jhub_credential, {}
        )
        resource_url = result["resource_url"]
        self.assertTrue(mocked_new_job.called)
        self.assertEqual(mocked_new_job.call_count, 1)

    def max_start_attempts_config():
        config = config_mock()
        config["systems"]["DEMO-SITE"]["pyunicore"]["job_description"][
            "replace_indicators"
        ] = ["<??", "??>"]
        config["systems"]["DEMO-SITE"]["pyunicore"]["job_description"]["hooks"][
            "project_kernel"
        ] = {"project": "myproject"}
        config["systems"]["DEMO-SITE"]["max_start_attempts"] = 5
        return config

    def get_minimal_config():
        return {
            "systems": {
                "mapping": {"system": {"DEMO-SITE": "default_system"}},
                "DEMO-SITE": {
                    "site_url": "https://localhost:8080/DEMO-SITE/rest/core",
                },
                "default_system": {
                    "pyunicore": {
                        "job_description": {
                            "base_directory": "web/tests/config/job_descriptions"
                        }
                    },
                },
            },
            "credential_mapping": {"authorized": "default_credential"},
        }

    @mock.patch(
        "requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=get_minimal_config)
    def test_start_job_pyunicore(
        self, mocked_config, mocked_requests, mocked_client, mcoked_transport
    ):
        config = PyUnicoreTests.get_minimal_config()
        data = copy.deepcopy(self.request_data_simple)
        data["user_options"]["vo"] = "myvo"
        data["env"] = {"JUPYTERHUB_USER_ID": 123}
        data["user_options"]["account"] = "myaccount"
        data["user_options"]["project"] = "myproject"
        data["user_options"]["partition"] = "devel"
        data["auth_state"] = {"access_token": "123"}

        instance_dict = {
            "user_options": data["user_options"],
            "servername": "random_uuid",
        }
        custom_headers = {"access-token": data["auth_state"]["access_token"]}

        ret = common.start_service(
            instance_dict, data, custom_headers, self.jhub_credential, {}
        )
        resource_url = ret["resource_url"]
        self.assertTrue(
            resource_url.startswith(config["systems"]["DEMO-SITE"]["site_url"])
        )
        self.assertEqual(
            len(resource_url),
            len(config["systems"]["DEMO-SITE"]["site_url"]) + 33,
        )

    @mock.patch(
        "requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    def test__pyunicore_get_job(self, mocked_requests, mocked_job, mocked_transport):
        global global_tmp_jobs
        global_tmp_jobs = []
        data = copy.deepcopy(self.request_data_simple)
        data["auth_state"] = {"access_token": "123"}
        data["user_options"]["account"] = "demouser"
        data["user_options"]["project"] = "demoproject"
        data["env"] = {"JUPYTERHUB_USER_ID": 17}
        self.setup_random_db_entries(
            data,
            5,
            add_to_db=True,
            tags=self.config["systems"]["default_system"]["pyunicore"]["cleanup"][
                "tags"
            ],
        )
        data["resource_url"] = global_tmp_jobs[0].resource_url
        # pyunicore._get_job(self.config, data["user_options"]["system"])

        j = pyunicore._get_job(
            self.config, data, {"access-token": data["auth_state"]["access_token"]}, {}
        )
        self.assertEqual(j.__class__.__name__, "MockJob")
        self.assertEqual(j.resource_url, global_tmp_jobs[0].resource_url)
