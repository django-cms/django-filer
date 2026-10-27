from django.core.management.base import BaseCommand
from django.db.models import Q

from filer.settings import FILER_IMAGE_MODEL
from filer.utils.loader import load_model
from filer.utils.provenance import detect_file_provenance


Image = load_model(FILER_IMAGE_MODEL)


class Command(BaseCommand):
    help = (
        "Detect provenance information - the IPTC digital source type and embedded "
        "C2PA Content Credentials - of images uploaded before filer detected it on "
        "upload. Only adds missing information: an upload validator such as "
        "strip_exif may have removed it from the stored file since."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help="Report what would be updated without changing the database.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        # Iterate over primary keys to keep memory consumption stable
        pks = list(
            Image.objects
            .filter(Q(digital_source_type='') | Q(has_content_credentials=False))
            .exclude(mime_type='image/svg+xml')
            .values_list('pk', flat=True)
        )
        updated = failed = 0
        for pk in pks:
            image = Image.objects.get(pk=pk)
            try:
                with image.file.storage.open(image.file.name, 'rb') as fh:
                    provenance = detect_file_provenance(fh)
            except Exception as e:
                failed += 1
                self.stderr.write(f"Failed to read image {image.pk} {image}: {e}")
                continue

            changes = {}
            if provenance.digital_source_type and not image.digital_source_type:
                changes['digital_source_type'] = provenance.digital_source_type
            if provenance.has_content_credentials and not image.has_content_credentials:
                changes['has_content_credentials'] = True
            if changes:
                updated += 1
                if options['verbosity'] > 1:
                    self.stdout.write(f"Image {image.pk} {image}: {changes}")
                if not dry_run:
                    # update() leaves the modification date and the file untouched
                    Image.objects.filter(pk=pk).update(**changes)

        self.stdout.write(
            f"Scanned {len(pks)} images, "
            f"{'would update' if dry_run else 'updated'} {updated}, failed {failed}."
        )
