from django.db import models


class TaskManager(models.Manager):
    def open_tasks(self):
        return self.filter(is_done=False).order_by("-created_at")

