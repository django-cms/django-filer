from django import forms
from filer.utils.files import get_valid_filename
from django.utils.translation import ugettext as _

class CopyFilesAndFoldersForm(forms.Form):
    suffix = forms.CharField(required=True, help_text=_("Suffix which will be appended to filenames of copied files."))
    # TODO: We have to find a way to overwrite files with different storage backends first.
    #overwrite_files = forms.BooleanField(required=False, help_text=_("Overwrite a file if there already exists a file with the same filename?"))

    def as_p_with_help(self):
        "Returns this form rendered as HTML <p>s with help text formated for admin."
        return self._html_output(
            normal_row = u'<p%(html_class_attr)s>%(label)s %(field)s</p>%(help_text)s',
            error_row = u'%s',
            row_ender = '</p>',
            help_text_html = u'<p class="help">%s</p>',
            errors_on_separate_row = True)

    def clean_suffix(self):
        valid = get_valid_filename(self.cleaned_data['suffix'])
        if valid != self.cleaned_data['suffix']:
            raise forms.ValidationError(_('Suffix should be a valid, simple and lowercase filename part, like "%(valid)s".') % {'valid': valid})
        return self.cleaned_data['suffix']
