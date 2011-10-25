from django.core.management.base import BaseCommand, CommandError
from filer.models import Video

class Command(BaseCommand):
    args = ''
    help = 'process next video conversion task'

    def handle(self, *args, **options):
        try:
            vid = Video.objects.filter(status='new')[0:1].get()
        except Video.DoesNotExist:
            self.stdout.write("No more tasks\n")
            return
        vid.status = 'process'
        vid.save()
        result, output = vid.convert()
        if result:
            vid.status = 'error'
        else:
            vid.status = 'ok'
        vid.output = output
        vid.save()
        self.stdout.write("Processed %s\n" % vid.file.name)
