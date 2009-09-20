DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '/tmp/filer.db' # won't actually be used. tests under SQLite are run in-memory
INSTALLED_APPS = ['filer']
ROOT_URLCONF = ['filer.urls']