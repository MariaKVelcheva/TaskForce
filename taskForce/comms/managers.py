from django.db import models


class ConversationManager(models.Manager):
    def visible_to(self, user):
        return self.filter(unit__memberships__user=user)

    def for_unit(self, unit):
        conversation, _ = self.get_or_create(unit=unit, task=None)
        return conversation

    def for_task(self, task):
        conversation, _ = self.get_or_create(unit=task.unit, task=task)
        return conversation