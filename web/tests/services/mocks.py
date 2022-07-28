import os
import uuid


def config_mock():
    return {
        "systems": {
            "mapping": {
                "replace_stage_specific": {
                    "stage1": {"stage_stuff": "stage1"},
                    "stage2": {"stage_stuff": "stage2"},
                },
                "replace_system_specific": {"DEMO-SITE": {}, "SYSTEM2": {}},
            },
            "DEMO-SITE": {
                "backend_id_env_name": "JUPYTER_BACKEND_ID",
                "site_url": "https://localhost:8080/DEMO-SITE/rest/core",
                "remote_nodes": ["demo_site"],
                "max_start_attempts": 3,
                "pyunicore": {
                    "job_archive": "/tmp/job-archive",
                    "transport": {
                        "certificate_path": False,
                        "oidc": False,
                        "timeout": 120,
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
                        "hooks": {
                            "load_project_specific_kernel": {
                                "project": ["training1904"],
                                "partition": ["devel"],
                            }
                        },
                        "input_directory_name": "input",
                        "resource_mapping": {
                            "resource_nodes": "Nodes",
                            "resource_Runtime": "Runtime",
                            "resource_gpus": "GPUs",
                        },
                        "interactive_partitions": {"LoginNode": "localost"},
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
                                "set_queue": False,
                            },
                        },
                    },
                },
            },
        }
    }


def config_mock_mapped():
    return {
        "systems": {
            "DEMO-SITE": {
                "backend_id_env_name": "JUPYTER_BACKEND_ID",
                "site_url": "https://localhost:8080/DEMO-SITE/rest/core",
                "remote_nodes": ["demo_site"],
                "max_start_attempts": 3,
                "pyunicore": {
                    "job_archive": "/tmp/job-archive",
                    "transport": {
                        "certificate_path": False,
                        "oidc": False,
                        "timeout": 120,
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
                        "hooks": {
                            "load_project_specific_kernel": {
                                "project": ["training1904"],
                                "partition": ["devel"],
                            }
                        },
                        "input_directory_name": "input",
                        "resource_mapping": {
                            "resource_nodes": "Nodes",
                            "resource_Runtime": "Runtime",
                            "resource_gpus": "GPUs",
                        },
                        "interactive_partitions": {"LoginNode": "localost"},
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
                                "set_queue": False,
                            },
                        },
                    },
                },
            }
        },
        "credential_mapping": {"authorized": "mapped"},
    }


class MockTransport:
    preferences = None
    oidc = False
    verify = False
    timeout = 120

    def __init__(self, oidc, verify, timeout, *args, **kwargs):
        self.oidc = oidc
        self.verify = verify
        self.timeout = timeout

    def _clone(self):
        tr = MockTransport(self.oidc, self.verify, self.timeout)
        tr.preferences = self.preferences
        return tr


class MockStorage:
    def __init__(self, transport, resource_url):
        self.resource_url = resource_url

    def listdir(self, base="/"):
        return {}


class MockJob:
    resource_url = ""
    properties = {}
    job_id = ""
    transport = None
    tags = []

    def __init__(self, transport, resource_url, tags=[]):
        self.resource_url = resource_url
        self.transport = transport
        self.job_id = os.path.basename(resource_url)
        self.tags = tags

    def is_running(self):
        return True

    def abort(self):
        pass

    def delete(self):
        pass

    @property
    def working_dir(self):
        return MockStorage(self.transport, self.resource_url)


def mocked_exception(*args, **kwargs):
    raise Exception("MockException")


def mocked_new_job(jd):
    site_url = "https://mocked:8080/mock/rest/core"
    uuidcode = uuid.uuid4().hex
    resource_url = f"{site_url}/{uuidcode}"
    job = MockJob(None, resource_url)
    return job


class MockClient:
    site_url = ""
    transport = None
    jobs = []
    job_description = {}

    def __init__(self, mock_transport, site_url):
        assert isinstance(mock_transport, MockTransport)
        self.transport = mock_transport
        self.site_url = site_url

    def new_job(self, job_description):
        assert isinstance(job_description, dict)
        assert len(job_description) != 0
        self.job_description = job_description
        uuidcode = uuid.uuid4().hex
        resource_url = f"{self.site_url}/{uuidcode}"
        job = MockJob(self.transport, resource_url)
        self.jobs.append(job)
        return job

    def store_jobs(self, jobs):
        self.jobs.extend(jobs)

    def get_jobs(self, tags=[]):
        ret = [x for x in self.jobs if x.tags == tags]
        return ret


def mocked_pyunicore_transport_init(
    auth_token=None, oidc=True, verify=False, timeout=120
):
    return MockTransport(oidc, verify, timeout)


def mocked_pyunicore_job_init(transport, resource_url):
    return MockJob(transport, resource_url)


def mocked_pyunicore_client_init(transport, site_url):
    return MockClient(transport, site_url)


def mocked_pass(*args, **kwargs):
    pass
