from django.db import models


class ServicesModel(models.Model):
    servername = models.TextField("servername")
    start_id = models.TextField("start_id")
    start_date = models.DateTimeField(auto_now_add=True)
    user_options = models.JSONField("user_options", default=dict)
    jhub_user_id = models.IntegerField("jhub_user_id", null=False)
    jhub_credential = models.TextField("jhub_credential", default="jupyterhub")
    resource_url = models.TextField("resource_url", default="")
    stop_pending = models.BooleanField(null=False, default=False)
