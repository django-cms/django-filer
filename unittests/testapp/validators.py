"""
Payload validators used to test the hook `finder.settings.FINDER_PAYLOAD_VALIDATORS`.
"""

calls = []


def recording_validator(file_name, file_handle, owner, mime_type):
    """A validator implemented as plain function."""
    calls.append({
        'file_name': file_name,
        'mime_type': mime_type,
        'owner': owner,
        'payload': file_handle.read(),
        'validator': 'recording_validator',
    })


class RecordingValidator:
    """A validator implemented as class. It is instantiated by `finder.models.file.payload_validator`."""

    def __call__(self, file_name, file_handle, owner, mime_type):
        calls.append({
            'file_name': file_name,
            'mime_type': mime_type,
            'owner': owner,
            'payload': file_handle.read(),
            'validator': 'RecordingValidator',
        })


def rejecting_validator(file_name, file_handle, owner, mime_type):
    raise ValueError(f"Payload of “{file_name}” rejected.")
