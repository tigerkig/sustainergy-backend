from django.apps import AppConfig


class SustainergyDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sustainergy_dashboard'

    def ready(self):
        import sustainergy_dashboard.signals
