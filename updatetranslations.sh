cd filer
django-admin.py makemessages -l en
tx push -s -l en
tx pull -f -a
django-admin.py compilemessages
