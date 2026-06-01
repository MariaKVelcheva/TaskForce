from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'taskForce.accounts'

    def ready(self):
        import taskForce.accounts.signals
