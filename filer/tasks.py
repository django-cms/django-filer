from celery import task

from django.core.management import call_command


@task
def take_out_filer_trash_task():
    call_command("take_out_filer_trash")
