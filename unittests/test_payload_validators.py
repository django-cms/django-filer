import pytest
import sys

from importlib.util import find_spec
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile

from finder.contrib.image.svg.models import SVGImageModel
from finder.contrib.image.svg.validators import svg_validator, xml_validator
from finder.models.file import FileModel, payload_validator

from .testapp import validators


VALID_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    b'<rect width="10" height="10"/>'
    b'</svg>'
)
MALFORMED_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect></svg>'
ENTITY_SVG = (
    b'<?xml version="1.0"?>'
    b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    b'<svg xmlns="http://www.w3.org/2000/svg">&xxe;</svg>'
)


requires_py_svg_hush = pytest.mark.skipif(
    find_spec('py_svg_hush') is None,
    reason="The optional package py_svg_hush is not installed.",
)
requires_defusedxml = pytest.mark.skipif(
    find_spec('defusedxml') is None,
    reason="The optional package defusedxml is not installed.",
)


@pytest.fixture(autouse=True)
def recorded_calls():
    validators.calls.clear()
    yield validators.calls
    validators.calls.clear()


@pytest.fixture
def register_validators(monkeypatch):
    def register(*entries):
        monkeypatch.setattr('finder.settings.FINDER_PAYLOAD_VALIDATORS', list(entries))

    return register


def upload(ambit, owner, name='small_file.bin', content=b'\x00' * 100, mime_type='application/octet-stream'):
    uploaded_file = SimpleUploadedFile(name, content, content_type=mime_type)
    model = FileModel.objects.get_model_for(mime_type)
    return model.objects.create_from_upload(ambit, uploaded_file, folder=ambit.root_folder, owner=owner)


def test_no_validators_configured(ambit, admin_user, register_validators, recorded_calls):
    register_validators()
    upload(ambit, admin_user)
    assert recorded_calls == []


def test_validator_for_exact_mime_type(ambit, admin_user, register_validators, recorded_calls):
    register_validators(('application/octet-stream', 'unittests.testapp.validators.recording_validator'))
    file_obj = upload(ambit, admin_user, content=b'\x01' * 12)
    assert len(recorded_calls) == 1
    assert recorded_calls[0] == {
        'file_name': file_obj.name,
        'mime_type': 'application/octet-stream',
        'owner': admin_user,
        'payload': b'\x01' * 12,
        'validator': 'recording_validator',
    }


def test_validator_for_wildcard_mime_type(ambit, admin_user, register_validators, recorded_calls):
    """A validator registered for “application/*” applies to every subtype."""
    register_validators(('application/*', 'unittests.testapp.validators.recording_validator'))
    upload(ambit, admin_user, name='sample.pdf', mime_type='application/pdf')
    assert [call['mime_type'] for call in recorded_calls] == ['application/pdf']


def test_validator_for_any_mime_type(ambit, admin_user, register_validators, recorded_calls):
    register_validators(('*/*', 'unittests.testapp.validators.recording_validator'))
    upload(ambit, admin_user, name='sample.pdf', mime_type='application/pdf')
    assert [call['mime_type'] for call in recorded_calls] == ['application/pdf']


def test_validator_for_other_mime_type_is_skipped(ambit, admin_user, register_validators, recorded_calls):
    register_validators(('image/png', 'unittests.testapp.validators.recording_validator'))
    upload(ambit, admin_user)
    assert recorded_calls == []


def test_multiple_validators_for_the_same_mime_type(ambit, admin_user, register_validators, recorded_calls):
    register_validators(
        ('application/octet-stream', 'unittests.testapp.validators.recording_validator'),
        ('application/octet-stream', 'unittests.testapp.validators.RecordingValidator'),
    )
    upload(ambit, admin_user)
    assert [call['validator'] for call in recorded_calls] == ['recording_validator', 'RecordingValidator']


def test_validator_given_as_callable(ambit, admin_user, register_validators, recorded_calls):
    register_validators(('application/octet-stream', validators.recording_validator))
    upload(ambit, admin_user)
    assert len(recorded_calls) == 1


def test_rejected_payload_aborts_the_upload(ambit, admin_user, register_validators):
    register_validators(('application/octet-stream', 'unittests.testapp.validators.rejecting_validator'))
    with pytest.raises(ValueError, match="Payload of “rejected.bin” rejected."):
        upload(ambit, admin_user, name='rejected.bin')
    assert FileModel.objects.filter(name='rejected.bin').exists() is False


def test_payload_validator_resolves_dotted_path_class_and_callable():
    assert payload_validator(validators.recording_validator) is validators.recording_validator
    assert payload_validator('unittests.testapp.validators.recording_validator') is validators.recording_validator
    assert isinstance(
        payload_validator('unittests.testapp.validators.RecordingValidator'),
        validators.RecordingValidator,
    )


def test_svg_validator_accepts_valid_svg():
    assert svg_validator('valid.svg', BytesIO(VALID_SVG), None, 'image/svg+xml') is None


@requires_py_svg_hush
def test_svg_validator_rejects_unparsable_content():
    with pytest.raises(ValueError, match="Invalid or malicious SVG in “broken.svg”"):
        svg_validator('broken.svg', BytesIO(b'this is not XML at all <<<'), None, 'image/svg+xml')


@requires_py_svg_hush
@pytest.mark.xfail(
    strict=True,
    reason="svg_validator() discards the sanitized output of filter_svg() and hence accepts scripted SVGs.",
)
def test_svg_validator_rejects_script_element():
    scripted_svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    with pytest.raises(ValueError):
        svg_validator('scripted.svg', BytesIO(scripted_svg), None, 'image/svg+xml')


def test_svg_validator_without_py_svg_hush(monkeypatch):
    """Without the optional dependency installed, the validator silently accepts everything."""
    monkeypatch.setitem(sys.modules, 'py_svg_hush', None)
    assert svg_validator('broken.svg', BytesIO(b'not XML <<<'), None, 'image/svg+xml') is None


def test_xml_validator_accepts_valid_svg():
    assert xml_validator('valid.svg', BytesIO(VALID_SVG), None, 'image/svg+xml') is None


@requires_defusedxml
def test_xml_validator_rejects_malformed_xml():
    with pytest.raises(ValueError, match="Invalid or malicious SVG in “broken.svg”"):
        xml_validator('broken.svg', BytesIO(MALFORMED_SVG), None, 'image/svg+xml')


@requires_defusedxml
def test_xml_validator_rejects_entity_declarations():
    """Entity declarations are the vector for XXE and billion laughs attacks."""
    with pytest.raises(ValueError):
        xml_validator('xxe.svg', BytesIO(ENTITY_SVG), None, 'image/svg+xml')


def test_xml_validator_without_defusedxml(monkeypatch):
    monkeypatch.setitem(sys.modules, 'defusedxml.ElementTree', None)
    assert xml_validator('broken.svg', BytesIO(MALFORMED_SVG), None, 'image/svg+xml') is None


@requires_py_svg_hush
def test_uploading_a_malformed_svg_is_rejected(ambit, admin_user, register_validators):
    register_validators(
        ('image/svg+xml', 'finder.contrib.image.svg.validators.svg_validator'),
        ('image/svg+xml', 'finder.contrib.image.svg.validators.xml_validator'),
    )
    with pytest.raises(ValueError, match="Invalid or malicious SVG in “broken.svg”"):
        upload(ambit, admin_user, name='broken.svg', content=b'not XML <<<', mime_type='image/svg+xml')
    assert SVGImageModel.objects.filter(name='broken.svg').exists() is False


def test_uploading_a_valid_svg_passes_validation(ambit, admin_user, register_validators):
    register_validators(
        ('image/svg+xml', 'finder.contrib.image.svg.validators.svg_validator'),
        ('image/svg+xml', 'finder.contrib.image.svg.validators.xml_validator'),
    )
    file_obj = upload(ambit, admin_user, name='valid.svg', content=VALID_SVG, mime_type='image/svg+xml')
    assert SVGImageModel.objects.filter(id=file_obj.id).exists() is True
    # svglib converts the pixel dimensions of the SVG into points
    assert (file_obj.width, file_obj.height) == (7.5, 7.5)
