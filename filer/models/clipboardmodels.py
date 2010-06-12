from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.contrib.auth import models as auth_models

class Clipboard(models.Model):
    user = models.ForeignKey(auth_models.User, related_name="filer_clipboards")
    files = models.ManyToManyField('File', related_name="in_clipboards", through='ClipboardItem')
    
    def append_file(self, file):
        newitem = ClipboardItem(file=file, clipboard=self)
        newitem.save()
    
    def empty(self):
        for item in self.bucket_items.all():
            item.delete()
    empty.alters_data = True
    
    
    def __unicode__(self):
        return u"Clipboard %s of %s" % (self.id, self.user)
    class Meta:
        app_label = 'filer'
        verbose_name = _('Clipboard')

class ClipboardItem(models.Model):
    file = models.ForeignKey('File')
    clipboard = models.ForeignKey(Clipboard)
    class Meta:
        app_label = 'filer'
        verbose_name = _('Clipboard item')
        verbose_name_plural = _('Clipboard items')