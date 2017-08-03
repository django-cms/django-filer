
# This script assumes a checkout of djangocms-publisher next to the django-filer
# checkout.
set -x
set -e
export DJANGOCMS_PUBLISHER_DIR="../../../../djangocms-publisher"
cp $DJANGOCMS_PUBLISHER_DIR/djangocms_publisher/models.py ./
# To create a new version of the patch edit the default for the field in
# models.py and run:
# git diff --relative > is_published-default.patch
patch models.py is_published-default.patch
cp $DJANGOCMS_PUBLISHER_DIR/djangocms_publisher/admin.py ./
cp $DJANGOCMS_PUBLISHER_DIR/djangocms_publisher/templates/admin/djangocms_publisher/tools/submit_line.html ../../templates/admin/filer/tools/
mkdir -p utils
cp $DJANGOCMS_PUBLISHER_DIR/djangocms_publisher/utils/__init__.py ./utils/
cp $DJANGOCMS_PUBLISHER_DIR/djangocms_publisher/utils/compat.py ./utils/
cp $DJANGOCMS_PUBLISHER_DIR/djangocms_publisher/utils/copying.py ./utils/
cp $DJANGOCMS_PUBLISHER_DIR/djangocms_publisher/utils/relations.py ./utils/
mkdir -p utils ./templatetags
cp $DJANGOCMS_PUBLISHER_DIR/djangocms_publisher/templatetags/__init__.py ./templatetags/
cp $DJANGOCMS_PUBLISHER_DIR/djangocms_publisher/templatetags/djangocms_publisher_admin_tags.py ./templatetags/
