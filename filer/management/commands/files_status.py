from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
# makes sure cms is loaded first
# import cms
from filer.utils.status import FileChecker


class Command(BaseCommand):

    help = "Checks wheather filer files exist on storage."

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--site_id',
            action='store',
            dest='site_id',
            type=int,
            help='Site Id'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            "Checking filer files. This might take a while...\n")

        every = 50
        times = 0

        def logger(stats):
            logger.times += 1
            if logger.times % every == 0:
                self.stdout.write("\n" + stats.progress())
        logger.times = 0

        site_id = options['site_id']
        self.stdout.write(f'The site  id {site_id} .')
        if site_id:
            try:
                site_obj = Site.objects.get(pk=site_id)
            except Site.DoesNotExist:
                self.stdout.write(f'The site with id {site_id} does not exist.')

            result_stats = FileChecker.check_site(site_id, log_progress=logger)
            self.stdout.write(result_stats.as_string(full=True))
        else:
            result_stats = FileChecker.check_all(log_progress=logger)
            self.stdout.write(result_stats.as_string(full=True))
