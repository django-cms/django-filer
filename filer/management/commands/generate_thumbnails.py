from django.core.management.base import BaseCommand

from filer.models.imagemodels import Image


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        Generates image thumbnails

        NOTE: To keep memory consumption stable avoid iteration over the Image queryset
        """
        pks = Image.objects.all().values_list('id', flat=True)
        total = len(pks)
        for idx, pk in enumerate(pks):
            image = None
            try:
                image = Image.objects.get(pk=pk)
                self.stdout.write(f'Processing image {idx + 1} / {total} {image}')
                self.stdout.flush()
                image.thumbnails
                image.icons
            except OSError as e:
                self.stderr.write(f'Failed to generate thumbnails: {str(e)}')
                self.stderr.flush()
            finally:
                del image
