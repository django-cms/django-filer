from django.core.management.base import BaseCommand
# makes sure cms is loaded first
import cms
from filer.utils.status import FileChecker


class Command(BaseCommand):

    help = "Checks wheather filer files exist on storage."

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

        result_stats = FileChecker.check_all(log_progress=logger)
        self.stdout.write(result_stats.as_string(full=True))
