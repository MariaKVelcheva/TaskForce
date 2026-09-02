from django.db import models


class TaskManager(models.Manager):
    def open_tasks(self):
        return self.filter(is_done=False).order_by("-created_at")

    def visible_to(self, user):
        return self.filter(Q(user=user) | Q(unit__users=user)).distinct()



