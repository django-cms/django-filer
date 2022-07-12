from django.core.management.base import BaseCommand
from filer.utils.checktrees import TreeChecker, TreeCorruption
from optparse import make_option


class Command(BaseCommand):

    help = "Fixes the folder mptt tree hierarchy (tree corruption)."

    def add_arguments(self, parser):
        parser.add_argument('--check',
                            action='store_true',
                            dest='checktree',
                            default=False,
                            help='Performs only a check for corrupted folder trees. '
                                 'Prints all the corruptions it finds.')
        parser.add_argument('--full-rebuild',
                            action='store_true',
                            dest='force_full_rebuild',
                            default=False,
                            help='Force a full tree rebuild.')

    def handle(self, *args, **options):
        checker = TreeChecker()
        if options['checktree']:
            try:
                self.stdout.write("Checking folder trees...\n")
                checker.find_corruptions()
            except TreeCorruption:
                if checker.full_rebuild:
                    self.stdout.write(
                        'There are multiple root folders with the same '
                        'tree_id. This will require a full rebuild.\n')
                else:
                    for folder_pk, msg in list(checker.corrupted_folders.items()):
                        self.stdout.write('Folder /%s:\n\t%s' % (
                            checker._get_folder_path(folder_pk), msg))
                        self.stdout.write('\n')
                    self.stdout.write(
                        "\nFollowing trees will require a rebuild\n")
                    for folder in checker.get_corrupted_root_nodes():
                        self.stdout.write('\n/%s' % folder.name)
                    self.stdout.write('\n')
            else:
                self.stdout.write("There are no corruptions\n")
        else:
            self.stdout.write("Checking folder tree...\n")
            checker.check_corruptions()
            if checker.full_rebuild or options['force_full_rebuild']:
                self.stdout.write("\nPerforming full rebuild...")
                checker.manager.rebuild()
            elif checker.corrupted_folders:
                self.stdout.write("\nPerforming corrupted folders rebuild...")
                for folder in checker.get_corrupted_root_nodes():
                    self.stdout.write(f"\n\tPerforming partial rebuild for folder {folder.name}")
                    checker.manager.partial_rebuild(folder.tree_id)
            else:
                self.stdout.write("There are no corruptions, nothign to be done.\n")
            self.stdout.write("\nRebuild Done.")
