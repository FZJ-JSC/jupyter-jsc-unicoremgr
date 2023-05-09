import os
from unittest import mock

from django.http.response import HttpResponse
from django.urls.base import reverse
from services.models import ServicesModel
from tests.user_credentials import mocked_requests_post_running
from tests.user_credentials import UserCredentials

from .mocks import config_mock
from .mocks import config_mock_mapped
from .mocks import config_mock_prefix
from .mocks import config_mock_suffix
from .mocks import mocked_exception
from .mocks import mocked_new_job
from .mocks import mocked_pass
from .mocks import mocked_pyunicore_client_init
from .mocks import mocked_pyunicore_client_newjob_fail
from .mocks import mocked_pyunicore_job_init
from .mocks import mocked_pyunicore_transport_init


class ServiceViewTests(UserCredentials):
    def test_health(self):
        url = "/api/health/"
        r = self.client.get(url, format="json")
        self.assertEqual(200, r.status_code)

    def mock_return_HttpResponse(*args, **kwargs):
        return HttpResponse()

    def mock_return_none(*args, **kwargs):
        pass

    simple_request_data = {
        "user_options": {
            "system": "DEMO-SITE",
            "service": "JupyterLab/simple",
            "project": "demoproject",
            "partition": "LoginNode",
            "account": "demouser",
        },
        "env": {
            "JUPYTERHUB_USER_ID": 17,
            "JUPYTERHUB_API_TOKEN": "secret",
            "JUPYTERHUB_STATUS_URL": "http://jhub:8000",
        },
        "start_id": "abcdefgh",
    }
    headers = {"access-token": "ZGVtb3VzZXI6dGVzdDEyMw=="}

    @mock.patch(
        "services.views.ServicesViewSet.create", side_effect=mock_return_HttpResponse
    )
    def test_viewset_create_called(self, mock):
        url = reverse("services-list")
        self.client.post(url, data={}, format="json")
        self.assertTrue(mock.called)

    def test_invalid_input_data(self):
        url = reverse("services-list")
        r = self.client.post(url, data={}, headers=self.headers, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), ["Missing key in input data: env"])

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create(
        self, config_mocked, transport_mocked, client_mocked, mocked_requests
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_newjob_fail,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_newjob_fail(
        self, config_mocked, transport_mocked, client_mocked, mocked_requests
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["detailed_error"], "NewJob Exception.")

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_newjob_fail,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock_prefix)
    @mock.patch("jupyterjsc_unicoremgr.decorators._config")
    def test_create_newjob_fail_prefix_errormsg(
        self,
        decorator_config,
        config_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        decorator_config.return_value = config_mock_prefix()
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        prefix_config = config_mock_prefix()
        prefix = prefix_config.get("unicore_status_message_prefix", {}).get(
            "NewJob Exception."
        )
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["detailed_error"], "NewJob Exception.")
        self.assertEqual(
            r.json()["error"], f"{prefix} UNICORE error during start process."
        )

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_newjob_fail,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock_suffix)
    @mock.patch("jupyterjsc_unicoremgr.decorators._config")
    def test_create_newjob_fail_suffix_errormsg(
        self,
        decorator_config,
        config_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        decorator_config.return_value = config_mock_suffix()
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        suffix_config = config_mock_suffix()
        suffix = suffix_config.get("unicore_status_message_suffix", {}).get(
            "NewJob Exception."
        )
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["detailed_error"], "NewJob Exception.")
        self.assertEqual(
            r.json()["error"], f"UNICORE error during start process. {suffix}"
        )

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_receive_id(
        self, config_mocked, transport_mocked, client_mocked, mocked_requests
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["id"], 1)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_auto_increment_id(
        self, config_mocked, transport_mocked, client_mocked, mocked_requests
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["id"], 1)
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["id"], 2)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_use_given_uuidcode(
        self, config_mocked, transport_mocked, client_mocked, mocked_requests
    ):
        import copy

        url = reverse("services-list")
        servername = "12345"
        headers = copy.deepcopy(self.headers)
        headers["uuidcode"] = servername
        r = self.client.post(
            f"{url}",
            data=self.simple_request_data,
            headers=headers,
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["servername"], servername)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_get_job(
        self,
        config_mocked,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 201)
        service_url = f"{url}{r.data['servername']}/"
        r = self.client.get(service_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["running"])

    @mock.patch(target="services.views.log.critical", side_effect=mocked_pass)
    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_delete_job(
        self,
        config_mocked,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
        mocked_log_critical,
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 201)
        service_url = f"{url}{r.data['servername']}/"
        r = self.client.delete(service_url, headers=self.headers)
        self.assertEqual(r.status_code, 204)
        self.assertFalse(mocked_log_critical.called)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_job_model_behaviour(
        self,
        config_mocked,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        url = reverse("services-list")
        objects = ServicesModel.objects.all()
        self.assertEqual(len(objects), 0)
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        objects = ServicesModel.objects.all()
        self.assertEqual(len(objects), 1)
        service_url = f"{url}{r.data['servername']}/"
        r = self.client.get(service_url, headers=self.headers)
        objects = ServicesModel.objects.all()
        self.assertEqual(len(objects), 1)
        r = self.client.delete(service_url, headers=self.headers)
        objects = ServicesModel.objects.all()
        self.assertEqual(len(objects), 0)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_job_get_exception_behaviour_transport_exception(
        self,
        config_mocked,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        service_url = f"{url}{r.data['servername']}/"
        patch = mock.patch(
            "services.utils.pyunicore.pyunicore.Transport", mocked_exception
        )
        patch.start()
        r = self.client.get(service_url, headers=self.headers)
        patch.stop()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["details"],
            {
                "error": "UNICORE error.",
                "detailed_error": "MockException",
            },
        )
        self.assertTrue(r.data["running"])

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.serializers._config", side_effect=config_mock_suffix)
    @mock.patch(target="services.utils.common._config", side_effect=config_mock_suffix)
    # @mock.patch("jupyterjsc_unicoremgr.decorators._config")
    def test_job_get_error_message_suffix(
        self,
        # decorator_config,
        config_mocked_suffix,
        config_mocked_suffix2,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        # decorator_config.return_value = config_mock_suffix()
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        service_url = f"{url}{r.data['servername']}/"
        patch = mock.patch(
            "services.utils.pyunicore.pyunicore.Transport", mocked_exception
        )
        patch.start()
        r = self.client.get(service_url, headers=self.headers)
        patch.stop()
        config_suffix = config_mocked_suffix()
        suffix = config_suffix.get("unicore_status_message_suffix", {}).get(
            "MockException", ""
        )
        self.assertEqual(r.status_code, 200)

        self.assertEqual(
            r.json()["details"],
            {
                "error": f"UNICORE error. {suffix}",
                "detailed_error": "MockException",
            },
        )
        self.assertTrue(r.data["running"])

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.serializers._config", side_effect=config_mock_prefix)
    @mock.patch(target="services.utils.common._config", side_effect=config_mock_prefix)
    # @mock.patch("jupyterjsc_unicoremgr.decorators._config")
    def test_job_get_error_message_prefix(
        self,
        # decorator_config,
        config_mocked_prefix2,
        config_mocked_prefix,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        # decorator_config.return_value = config_mock_prefix()
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        service_url = f"{url}{r.data['servername']}/"
        patch = mock.patch(
            "services.utils.pyunicore.pyunicore.Transport", mocked_exception
        )
        patch.start()
        r = self.client.get(service_url, headers=self.headers)
        patch.stop()
        config_prefix = config_mock_prefix()
        prefix = config_prefix.get("unicore_status_message_prefix", {}).get(
            "MockException", ""
        )
        self.assertEqual(r.status_code, 200)

        self.assertEqual(
            r.json()["details"],
            {
                "error": f"{prefix} UNICORE error.",
                "detailed_error": "MockException",
            },
        )
        self.assertTrue(r.data["running"])

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_job_get_exception_behaviour_job_init_exception(
        self,
        config_mocked,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        service_url = f"{url}{r.data['servername']}/"
        patch = mock.patch("services.utils.pyunicore.pyunicore.Job", mocked_exception)
        patch.start()
        r = self.client.get(service_url, headers=self.headers)
        patch.stop()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["details"],
            {
                "error": "UNICORE error during status process.",
                "detailed_error": "MockException",
            },
        )
        self.assertTrue(r.data["running"])

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_job_get_exception_behaviour_job_is_running_exception(
        self,
        config_mocked,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        service_url = f"{url}{r.data['servername']}/"
        patch = mock.patch("tests.services.mocks.MockJob.is_running", mocked_exception)
        patch.start()
        r = self.client.get(service_url, headers=self.headers)
        patch.stop()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["details"],
            {
                "error": "UNICORE error during status process.",
                "detailed_error": "MockException",
            },
        )
        self.assertTrue(r.data["running"])

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_exception_behaviour_top_level_error(
        self, config_mocked, transport_mocked, client_mocked, mocked_requests
    ):
        url = reverse("services-list")
        patch = mock.patch(
            "services.views.ServicesViewSet.perform_create", mocked_exception
        )
        patch.start()

        # patch = mock.patch("tests.services.mocks.MockJob.is_running", mocked_exception)
        # patch.start()
        # r = self.client.get(service_url)

        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        patch.stop()
        self.assertEqual(r.status_code, 500)
        self.assertEqual(
            r.json(), {"error": "Unexpected Error", "detailed_error": "MockException"}
        )

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_delete_exception_behaviour_stop_service_error(
        self, config_mocked, transport_mocked, client_mocked, mocked_requests
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 201)
        objects = ServicesModel.objects.all()
        self.assertEqual(len(objects), 1)
        service_url = f"{url}{r.data['servername']}/"
        patch = mock.patch("services.utils.common.stop_service", mocked_exception)
        patch.start()
        r = self.client.delete(service_url, headers=self.headers)
        self.assertEqual(r.status_code, 204)
        patch.stop()
        objects = ServicesModel.objects.all()
        self.assertEqual(len(objects), 0)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_show_data_user_specific(
        self,
        config_mocked,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )

        rg1 = self.client.get(url, format="json")
        self.assertEqual(len(rg1.data), 1)

        self.client.credentials(**self.credentials_authorized_2)
        rg2 = self.client.get(url, format="json")
        self.assertEqual(len(rg2.data), 0)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Job",
        side_effect=mocked_pyunicore_job_init,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_cannot_delete_other_services(
        self,
        config_mocked,
        job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        rg1 = self.client.get(url, headers=self.headers, format="json")
        self.assertEqual(len(rg1.data), 1)

        self.client.credentials(**self.credentials_authorized_2)
        rd2 = self.client.delete(
            f"{url}{rg1.data[0]['servername']}/", headers=self.headers, format="json"
        )
        self.assertEqual(rd2.status_code, 404)

        self.client.credentials(**self.credentials_authorized)
        rd1 = self.client.delete(
            f"{url}{rg1.data[0]['servername']}/", headers=self.headers, format="json"
        )
        self.assertEqual(rd1.status_code, 204)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="tests.services.mocks.MockClient.new_job", side_effect=mocked_new_job
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    @mock.patch.dict(os.environ, {"STAGE": "stage1"})
    def test_skip_replace_stage(
        self,
        config_mocked,
        new_job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)
        job_args = new_job_mocked.call_args.args[0]
        start_sh = [x["Data"] for x in job_args["Imports"] if x["To"] == "start.sh"]
        stage_specific = [
            x.split(": ")[1]
            for x in start_sh[0].split("\n")
            if x.startswith("#StageSpecific: ")
        ][0]
        config = config_mock()
        stage_specific_configured = (
            config.get("systems", {})
            .get("mapping", {})
            .get("replace", {})
            .get("stage", {})
            .get("stage1", {})
            .get("stage_stuff", None)
        )
        self.assertEqual(stage_specific, stage_specific_configured)
        self.assertIsNotNone(stage_specific_configured)

    @mock.patch(
        target="requests.post",
        side_effect=mocked_requests_post_running,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Client",
        side_effect=mocked_pyunicore_client_init,
    )
    @mock.patch(
        target="services.utils.pyunicore.pyunicore.Transport",
        side_effect=mocked_pyunicore_transport_init,
    )
    @mock.patch(
        target="tests.services.mocks.MockClient.new_job", side_effect=mocked_new_job
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    @mock.patch.dict(os.environ, {"STAGE": "stage1"})
    def test_skip_other_system(
        self,
        config_mocked,
        new_job_mocked,
        transport_mocked,
        client_mocked,
        mocked_requests,
    ):
        url = reverse("services-list")
        r = self.client.post(
            url, data=self.simple_request_data, headers=self.headers, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)
        job_args = new_job_mocked.call_args.args[0]
        file_txt = [x["Data"] for x in job_args["Imports"] if x["To"] == "file.txt"]
        self.assertEqual(len(file_txt), 0)
        file_txt = [
            x["Data"] for x in job_args["Imports"] if x["To"] == "SYSTEM2_file.txt"
        ]
        self.assertEqual(len(file_txt), 0)
