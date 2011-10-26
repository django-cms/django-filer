from django.core.management.base import BaseCommand, CommandError
from filer.models import Video


class Command(BaseCommand):
    args = ''
    help = 'Processes next video conversion task'

    def handle(self, *args, **options):
        try:
            vid = Video.objects.filter(conversion_status='new')[0:1].get()
        except Video.DoesNotExist:
            self.stdout.write("No more tasks\n")
            return
        vid.conversion_status = 'process'
        vid.save()
        try:
            result, output = vid.convert()
        except Exception:
            vid.conversion_status = 'error'
            import traceback
            vid.conversion_output = traceback.format_exc()
        else:
            vid.conversion_status = 'ok' if not result else 'error'
            vid.conversion_output = output
        vid.save()
        if vid.conversion_status == 'ok':
            self.stdout.write("Processed %s\n" % vid.file.name)
        else:
            self.stdout.write("Failed to process %s (check conversion_output field for more info)\n" % vid.file.name)
