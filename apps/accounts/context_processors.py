from .models import SiteConfiguration

def site_configuration(request):
    config = SiteConfiguration.objects.first()
    return {
        'support_email': config.support_email if config else 'soporte@ahhh-ibiza.com',
        'maintenance_mode': config.maintenance_mode if config else False
    }
