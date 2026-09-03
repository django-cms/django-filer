import pytest
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from finder.exceptions import FileValidationError
from finder.models.file import FileModel
from finder import validators


calls = []


def record(file_name, file, owner, mime_type):
    """A validator that accepts everything and remembers how it was called."""
    calls.append((file_name, file.read(), owner, mime_type))


def reject(file_name, file, owner, mime_type):
    raise FileValidationError(f'File “{file_name}”: nope')


def reject_with_value_error(file_name, file, owner, mime_type):
    raise ValueError('not a valid payload')


def shout(file_name, file, owner, mime_type):
    """A sanitizing validator: it rewrites the payload rather than rejecting it."""
    content = file.read()
    file.seek(0)
    file.truncate()
    file.write(content.upper())


class RecordingValidator:
    """Validators may be classes; finder instantiates them once."""
    def __call__(self, file_name, file, owner, mime_type):
        calls.append((file_name, file.read(), owner, mime_type))


class RejectingValidator:
    def __call__(self, file_name, file, owner, mime_type):
        raise FileValidationError('class says no')


@pytest.fixture(autouse=True)
def clear_calls():
    calls.clear()
    yield
    calls.clear()


def upload(ambit, owner, content=b'hello', name='payload.txt', mime_type='text/plain'):
    return FileModel.objects.get_model_for(mime_type).objects.create_from_upload(
        ambit,
        SimpleUploadedFile(name, content, content_type=mime_type),
        folder=ambit.root_folder,
        owner=owner,
    )


class TestConfiguration:
    def test_defaults_are_applied(self):
        assert validators.get_validators('text/html') == [validators.deny_html]
        for mime_type in ['application/xhtml+xml', 'application/xml', 'text/xml', 'application/xslt+xml']:
            assert validators.get_validators(mime_type) == [validators.deny]

    def test_unknown_binaries_are_not_denied_by_default(self):
        # A deliberate deviation from django-filer: FileModel is finder's documented
        # fallback for everything that matches no other model.
        assert validators.get_validators('application/octet-stream') == []

    def test_the_mapping_shape_adds_to_the_defaults(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/html': [record]}
        assert validators.get_validators('text/html') == [validators.deny_html, record]

    def test_a_bare_validator_needs_no_list(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': record}
        assert validators.get_validators('text/plain') == [record]

    def test_the_legacy_tuple_shape_is_still_accepted(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = [('text/plain', record), ('text/plain', reject)]
        assert validators.get_validators('text/plain') == [record, reject]

    def test_defaults_can_be_removed(self, settings):
        settings.FINDER_REMOVE_PAYLOAD_VALIDATORS = ['text/html', 'image/svg+xml']
        assert validators.get_validators('text/html') == []
        assert validators.get_validators('image/svg+xml') == []

    def test_removal_precedes_addition(self, settings):
        settings.FINDER_REMOVE_PAYLOAD_VALIDATORS = ['text/html']
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/html': [record]}
        assert validators.get_validators('text/html') == [record]

    def test_dotted_paths_are_imported(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': ['finder.validators.deny']}
        assert validators.get_validators('text/plain') == [validators.deny]

    def test_an_unimportable_validator_is_reported(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': ['finder.validators.no_such_validator']}
        with pytest.raises(ImproperlyConfigured, match='Could not import'):
            validators.get_validators('text/plain')

    def test_a_non_callable_validator_is_reported(self):
        with pytest.raises(ImproperlyConfigured, match='not callable'):
            validators.payload_validator(42)

    def test_classes_are_instantiated(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [RecordingValidator]}
        resolved = validators.get_validators('text/plain')
        assert isinstance(resolved[0], RecordingValidator)

    def test_a_dotted_path_to_a_class_is_instantiated(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {
            'text/plain': ['unittests.test_validation.RecordingValidator'],
        }
        resolved = validators.get_validators('text/plain')
        assert isinstance(resolved[0], RecordingValidator)

    def test_an_instance_is_used_as_it_is(self, settings):
        instance = RecordingValidator()
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [instance]}
        assert validators.get_validators('text/plain') == [instance]

    def test_a_class_is_instantiated_once(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [RecordingValidator]}
        first = validators.get_validators('text/plain')[0]
        assert validators.get_validators('text/plain')[0] is first


class TestMatching:
    def test_subtype_wildcard(self, settings):
        # This is the match that used to be dead code: '{0}/*'.format(mime.split('/'))
        # formats the whole list, so it never equalled 'image/*'.
        settings.FINDER_PAYLOAD_VALIDATORS = {'image/*': [record]}
        assert validators.get_validators('image/png') == [record]
        # the wildcard match precedes the exact-match default for SVG
        assert validators.get_validators('image/svg+xml')[0] == record
        assert validators.get_validators('text/plain') == []

    def test_catch_all_wildcard(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'*/*': [record]}
        assert validators.get_validators('text/plain') == [record]
        assert validators.get_validators('application/octet-stream') == [record]

    def test_general_matches_run_before_specific_ones(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {
            'image/png': [reject],
            '*/*': [record],
            'image/*': [shout],
        }
        assert validators.get_validators('image/png') == [record, shout, reject]

    def test_a_missing_mime_type_is_treated_as_unknown(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'application/octet-stream': [record]}
        validators.validate_payload('f.bin', SimpleUploadedFile('f.bin', b'x'), None, None)
        assert len(calls) == 1
        assert calls[0][3] == 'application/octet-stream'


class TestValidatePayload:
    def test_the_validator_signature(self, settings, admin_user):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [record]}
        validators.validate_payload('note.txt', SimpleUploadedFile('note.txt', b'hi'), admin_user, 'text/plain')
        assert calls == [('note.txt', b'hi', admin_user, 'text/plain')]

    def test_each_validator_gets_the_file_rewound(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [record, record]}
        validators.validate_payload('note.txt', SimpleUploadedFile('note.txt', b'hi'), None, 'text/plain')
        assert [content for _, content, _, _ in calls] == [b'hi', b'hi']

    def test_the_file_is_left_rewound(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [record]}
        payload = SimpleUploadedFile('note.txt', b'hi')
        validators.validate_payload('note.txt', payload, None, 'text/plain')
        assert payload.tell() == 0

    def test_a_value_error_becomes_a_validation_error(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [reject_with_value_error]}
        with pytest.raises(FileValidationError) as caught:
            validators.validate_payload('note.txt', SimpleUploadedFile('note.txt', b'hi'), None, 'text/plain')
        assert caught.value.messages == ['not a valid payload']

    def test_a_validation_error_passes_through(self, settings):
        # This is the shape django-filer's validators raise.
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [reject]}
        with pytest.raises(ValidationError) as caught:
            validators.validate_payload('note.txt', SimpleUploadedFile('note.txt', b'hi'), None, 'text/plain')
        assert caught.value.messages == ['File “note.txt”: nope']

    def test_a_sanitizing_validator_rewrites_the_payload(self, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [shout]}
        payload = SimpleUploadedFile('note.txt', b'hi')
        validators.validate_payload('note.txt', payload, None, 'text/plain')
        assert payload.read() == b'HI'


@pytest.mark.django_db
class TestUpload:
    def test_a_rejected_upload_raises(self, ambit, admin_user, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [reject]}
        with pytest.raises(ValidationError):
            upload(ambit, admin_user)

    def test_a_rejected_upload_stores_nothing(self, ambit, admin_user, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [reject]}
        before = FileModel.objects.count()
        with pytest.raises(ValidationError):
            upload(ambit, admin_user)
        assert FileModel.objects.count() == before
        # nothing was written to storage either: validation runs before the payload lands
        with patch.object(type(ambit.original_storage), 'save') as save:
            with pytest.raises(ValidationError):
                upload(ambit, admin_user)
        save.assert_not_called()

    def test_html_is_denied_by_default(self, ambit, admin_user):
        with pytest.raises(ValidationError, match='HTML upload denied'):
            upload(ambit, admin_user, b'<h1>hi</h1>', 'page.html', 'text/html')

    def test_binaries_are_accepted_by_default(self, ambit, admin_user):
        file = upload(ambit, admin_user, b'\x00\x01', 'blob.bin', 'application/octet-stream')
        assert file.file_size == 2

    @pytest.mark.parametrize('configured', [
        record,                                        # a callable
        'unittests.test_validation.record',            # a dotted path
        RecordingValidator,                            # a class, instantiated by finder
        'unittests.test_validation.RecordingValidator',  # a dotted path to a class
    ])
    def test_every_resolution_form_runs_on_upload(self, ambit, admin_user, settings, configured):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [configured]}
        upload(ambit, admin_user, b'hello', 'resolved.txt')
        assert calls == [('resolved.txt', b'hello', admin_user, 'text/plain')]

    def test_a_class_based_validator_can_reject(self, ambit, admin_user, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [RejectingValidator]}
        with pytest.raises(ValidationError, match='class says no'):
            upload(ambit, admin_user)

    def test_a_sanitized_payload_is_what_gets_stored(self, ambit, admin_user, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [shout]}
        file = upload(ambit, admin_user, b'hello')
        with ambit.original_storage.open(file.file_path) as handle:
            assert handle.read() == b'HELLO'

    def test_size_and_hash_follow_the_sanitized_payload(self, ambit, admin_user, settings):
        plain = upload(ambit, admin_user, b'hello', 'plain.txt')
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [
            lambda file_name, file, owner, mime_type: (file.seek(0), file.truncate(), file.write(b'longer!!')),
        ]}
        sanitized = upload(ambit, admin_user, b'hello', 'sanitized.txt')
        assert sanitized.file_size == 8
        assert sanitized.sha1 != plain.sha1

    def test_copying_a_file_does_not_revalidate_it(self, ambit, admin_user, sub_folder, settings):
        file = upload(ambit, admin_user)
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [reject]}
        copy = file.copy_to(ambit, admin_user, sub_folder)
        assert copy.file_size == file.file_size


@pytest.mark.django_db
class TestSanitizeSvg:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><script>alert(1)</script></svg>'

    def test_scripting_is_removed_from_the_stored_document(self, ambit, admin_user):
        pytest.importorskip('py_svg_hush')
        file = upload(ambit, admin_user, self.svg, 'drawing.svg', 'image/svg+xml')
        with ambit.original_storage.open(file.file_path) as handle:
            assert b'script' not in handle.read()

    def test_it_fails_closed_without_py_svg_hush(self, ambit, admin_user):
        with patch.dict('sys.modules', {'py_svg_hush': None}):
            with pytest.raises(ValidationError, match='py-svg-hush is not installed'):
                upload(ambit, admin_user, self.svg, 'drawing2.svg', 'image/svg+xml')


@pytest.mark.django_db
class TestViews:
    def test_the_upload_endpoint_reports_the_rejection(self, admin_client, ambit, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'text/plain': [reject]}
        url = reverse('finder-api:base-url') + f'{ambit.root_folder_id}/upload'
        response = admin_client.post(
            url,
            {'upload_file': SimpleUploadedFile('note.txt', b'hi', content_type='text/plain')},
            content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
        )
        assert response.status_code == 422
        assert response.json() == {'error': ['File “note.txt”: nope']}

    def test_replacing_a_file_reports_the_rejection(self, admin_client, ambit, uploaded_file, settings):
        settings.FINDER_PAYLOAD_VALIDATORS = {'application/octet-stream': [reject]}
        base_url = reverse('admin:finder_filemodel_changelist')
        response = admin_client.post(
            f'{base_url}{uploaded_file.id}/upload',
            {'upload_file': SimpleUploadedFile(
                'small_file.bin', b'replacement', content_type='application/octet-stream')},
            content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
        )
        assert response.status_code == 400
        assert 'nope' in response.content.decode()
        uploaded_file.refresh_from_db()
        assert uploaded_file.file_size != len(b'replacement')
