import pytest
from bs4 import BeautifulSoup
from io import BytesIO

from enum import Enum, auto
from PIL import Image, ImageDraw

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from finder.models.permission import AccessControlEntry, Privilege


class AccessControl(Enum):
    ALLOW = auto()
    READ_ONLY = auto()


@pytest.mark.parametrize('access_control', [AccessControl.ALLOW, AccessControl.READ_ONLY, None])
def test_replace_image(admin_client, admin_user, ambit, uploaded_image, access_control, principal_kwargs):
    base_url = reverse('admin:finder_filemodel_changelist')
    upload_url = f'{base_url}{uploaded_image.id}/upload'
    original_sha1 = uploaded_image.sha1
    new_image = Image.new('RGB', (960, 960), color=(128, 128, 128))

    if admin_user.is_superuser:
        if access_control is not None:
            return  # skip redundant test cases where superuser has access regardless of ACL
    else:
        AccessControlEntry.objects.all().delete()
        if access_control == AccessControl.ALLOW:
            AccessControlEntry.objects.create(inode=uploaded_image.id, **principal_kwargs)
        elif access_control == AccessControl.READ_ONLY:
            principal_kwargs['privilege'] = Privilege.READ
            AccessControlEntry.objects.create(inode=uploaded_image.id, **principal_kwargs)

    # replace image with same MIME type
    buffer = BytesIO()
    new_image.save(buffer, format='PNG')
    replacement_image = SimpleUploadedFile('grey.png', buffer.getvalue(), content_type='image/png')
    response = admin_client.post(
        upload_url,
        {'upload_file': replacement_image},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    if admin_user.is_superuser or access_control == AccessControl.ALLOW:
        assert response.status_code == 200
    else:
        assert response.status_code == 403
        return

    uploaded_image.refresh_from_db()
    assert uploaded_image.file_size == buffer.tell()
    assert uploaded_image.sha1 != original_sha1
    original_sha1 = uploaded_image.sha1
    assert uploaded_image.width == 960
    assert uploaded_image.height == 960

    # replace image with alternative MIME type
    buffer = BytesIO()
    new_image.save(buffer, format='JPEG')
    replacement_image = SimpleUploadedFile('grey.jpeg', buffer.getvalue(), content_type='image/jpeg')
    response = admin_client.post(
        upload_url,
        {'upload_file': replacement_image},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    assert response.status_code == 400
    assert response.text == "Can not replace file test_image.png with different mime type."
    uploaded_image.refresh_from_db()
    assert uploaded_image.sha1 == original_sha1
    assert uploaded_image.width == 960
    assert uploaded_image.height == 960


def test_get_image_admin(admin_client, ambit, uploaded_image):
    admin_url = f'/admin/finder/{ambit.slug}/{uploaded_image.id}'
    response = admin_client.get(admin_url)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.title.string == f"{uploaded_image.name} | Change Web Image | Django site admin"
    # file_details = soup.find('div', class_='file-details')
    # assert file_details is not None
    # assert file_details.find('h2').string == uploaded_image.name
    # assert file_details.find('img')['src'] == uploaded_image.file.url
    # <div class=""><h2>20210604_145345.jpg</h2><div class="ReactCrop"><div class="ReactCrop__child-wrapper"><img class="editable" src="/media/finder_demo/2b/94/2b947dbf-d0c6-4a73-9633-10b4db5ce155/Karius_und_Baktus.jpg"></div></div><div class="button-group"><button type="button"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M 7.3652344 1.9746094 L 5.6347656 2.9746094 L 6.2265625 4 L 4 4 L 4 7 L 7 7 L 7 5.3398438 L 14.310547 18 L 14 18 L 14 19 L 14.888672 19 L 16.634766 22.025391 L 18.365234 21.025391 L 17.773438 20 L 20 20 L 20 17 L 17 17 L 17 18.660156 L 9.6894531 6 L 10 6 L 10 5 L 9.1113281 5 L 7.3652344 1.9746094 z M 17 4 L 17 7 L 20 7 L 20 4 L 17 4 z M 5 5 L 6 5 L 6 6 L 5 6 L 5 5 z M 11 5 L 11 6 L 13 6 L 13 5 L 11 5 z M 14 5 L 14 6 L 16 6 L 16 5 L 14 5 z M 18 5 L 19 5 L 19 6 L 18 6 L 18 5 z M 5 8 L 5 10 L 6 10 L 6 8 L 5 8 z M 18 8 L 18 10 L 19 10 L 19 8 L 18 8 z M 5 11 L 5 13 L 6 13 L 6 11 L 5 11 z M 18 11 L 18 13 L 19 13 L 19 11 L 18 11 z M 5 14 L 5 16 L 6 16 L 6 14 L 5 14 z M 18 14 L 18 16 L 19 16 L 19 14 L 18 14 z M 4 17 L 4 20 L 7 20 L 7 17 L 4 17 z M 5 18 L 6 18 L 6 19 L 5 19 L 5 18 z M 8 18 L 8 19 L 10 19 L 10 18 L 8 18 z M 11 18 L 11 19 L 13 19 L 13 18 L 11 18 z M 18 18 L 19 18 L 19 19 L 18 19 L 18 18 z "></path></svg>Clear selection</button><div role="combobox" aria-haspopup="listbox" aria-expanded="false" aria-disabled="false" class="with-caret"><div data-state="closed">Gravity: Center</div><ul role="listbox"><li value="" role="option" aria-selected="true"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="m 19.650602,19.184 1.177984,1.178637 0.921354,-0.92157 6e-5,2.310036 -2.309571,1.2e-5 0.921565,-0.921778 L 19.184,19.65069 Z m -15.301204,0 -1.177984,1.178637 -0.921354,-0.92157 -6e-5,2.310036 2.309571,1.2e-5 L 3.638006,20.829337 4.816,19.65069 Z m 0,-14.366885 L 3.171414,3.638478 2.25006,4.560048 2.25,2.250012 4.559571,2.25 3.638006,3.171778 4.816,4.350425 Z m 15.301204,0 1.177984,-1.178637 0.921354,0.92157 L 21.75,2.250012 19.440429,2.25 20.361994,3.171778 19.184,4.350425 Z M 17,12.666 v 2 h 1 v -2 z m -11,0 v 2 h 1 v -2 z M 9.333,17 v 1 h 2 v -1 z m 3.333,0 v 1 h 2 v -1 z m 0,-11 v 1 h 2 V 6 Z M 9.333,6 v 1 h 2 V 6 Z M 6,9.333 v 2 h 1 v -2 z m 11,0 v 2 h 1 v -2 z M 16,16 v 3 h 3 v -3 z m 1,1 h 1 v 1 H 17 Z M 5,16 v 3 h 3 v -3 z m 1,1 h 1 v 1 H 6 Z M 0,0 V 24 H 24 V 0 Z M 1,1 H 23 V 23 H 1 Z m 15,4 v 3 h 3 V 5 Z m 1,1 h 1 V 7 H 17 Z M 5,5 V 8 H 8 V 5 Z M 6,6 H 7 V 7 H 6 Z" style="stroke-width: 0.329968;"></path></svg>Center</li><li value="n" role="option" aria-selected="false"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M 18.717,10.232048 20.839166,3.70167 19.599675,3.298966 21.657905,2.250179 22.706639,4.30841 21.466866,3.90561 19.344697,10.436 Z m -13.4343369,0 L 3.1604974,3.70167 4.3999884,3.298966 2.3417578,2.250179 1.2930239,4.30841 2.5327967,3.90561 4.6549659,10.436 Z M 16,14 h 3 v -3 h -3 z m 1,-1 v -1 h 1 v 1 z m -4.334,0 h 2 v -1 h -2 z M 17,20.667 h 1 v -2 h -1 z m 0,-3.333 h 1 v -2 h -1 z m -11,0 h 1 v -2 H 6 Z m 1,3.333 H 6 v -2 H 7 Z M 9.333,13 h 2 v -1 h -2 z M 0,24 H 24 V 0 H 0 Z M 1,23 V 1 H 23 V 23 Z M 5,14 H 8 V 11 H 5 Z m 1,-1 v -1 h 1 v 1 z M 5,23 H 8 V 22 H 5 Z m 11,0 h 3 v -1 h -3 z" style="stroke-width: 0.33;"></path></svg>North</li><li value="ne" role="option" aria-selected="false"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M 13.367,10.165753 20.36159,3.17159 19.440021,2.250059 21.750057,2.25 l 1.1e-5,2.310013 -0.921778,-0.921742 -6.9946,6.994173 z M 11,17.334 v -2 h 1 v 2 z M 3.333,13 v -1 h 2 v 1 z m 3.333,0 v -1 h 2 v 1 z M 10,23 v -1 h 3 v 1 z M 1,14 v -3 h 1 v 3 z m 10,6.667 v -2 h 1 v 2 z M 10,14 v -3 h 3 v 3 z m 1,-1 h 1 V 12 H 11 Z M 0,24 V 0 H 24 V 24 Z M 1,23 H 23 V 1 H 1 Z" style="stroke-width: 0.33;"></path></svg>Northeast</li><li value="e" role="option" aria-selected="false"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="m 13.767952,18.717 6.530378,2.122166 0.402704,-1.239491 1.048787,2.05823 -2.058231,1.048734 0.4028,-1.239773 -6.53039,-2.122169 z m 0,-13.4343369 6.530378,-2.1221657 0.402704,1.239491 L 21.749821,2.3417578 19.69159,1.2930239 20.09439,2.5327967 13.564,4.6549659 Z M 10,16 v 3 h 3 v -3 z m 1,1 h 1 v 1 h -1 z m 0,-4.334 v 2 h 1 v -2 z M 3.333,17 v 1 h 2 v -1 z m 3.333,0 v 1 h 2 v -1 z m 0,-11 v 1 h 2 V 6 Z M 3.333,7 V 6 h 2 V 7 Z M 11,9.333 v 2 h 1 v -2 z M 0,0 V 24 H 24 V 0 Z M 1,1 H 23 V 23 H 1 Z m 9,4 v 3 h 3 V 5 Z m 1,1 h 1 V 7 H 11 Z M 1,5 V 8 H 2 V 5 Z m 0,11 v 3 h 1 v -3 z" style="stroke-width: 0.33;"></path></svg>East</li><li value="se" role="option" aria-selected="false"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="m 13.367,13.834247 6.99459,6.994163 -0.921569,0.921531 2.310036,5.9e-5 1.1e-5,-2.310013 -0.921778,0.921742 -6.9946,-6.994173 z M 11,6.666 v 2 h 1 v -2 z M 3.333,11 v 1 h 2 v -1 z m 3.333,0 v 1 h 2 V 11 Z M 10,1 v 1 h 3 V 1 Z m -9,9 v 3 H 2 V 10 Z M 11,3.333 v 2 h 1 v -2 z M 10,10 v 3 h 3 v -3 z m 1,1 h 1 v 1 H 11 Z M 0,0 V 24 H 24 V 0 Z M 1,1 H 23 V 23 H 1 Z" style="stroke-width: 0.33;"></path></svg>Southeast</li><li value="s" role="option" aria-selected="false"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="m 18.717,13.767952 2.122166,6.530378 -1.239491,0.402704 2.05823,1.048787 1.048734,-2.058231 -1.239773,0.4028 -2.122169,-6.53039 z m -13.4343369,0 -2.1221657,6.530378 1.239491,0.402704 L 2.3417578,21.749821 1.2930239,19.69159 2.5327967,20.09439 4.6549659,13.564 Z M 16,10 h 3 v 3 h -3 z m 1,1 v 1 h 1 v -1 z m -4.334,0 h 2 v 1 h -2 z M 17,3.333 h 1 v 2 h -1 z m 0,3.333 h 1 v 2 h -1 z m -11,0 h 1 v 2 H 6 Z M 7,3.333 H 6 v 2 H 7 Z M 9.333,11 h 2 v 1 h -2 z M 0,0 H 24 V 24 H 0 Z M 1,1 V 23 H 23 V 1 Z m 4,9 h 3 v 3 H 5 Z m 1,1 v 1 H 7 V 11 Z M 5,1 H 8 V 2 H 5 Z m 11,0 h 3 v 1 h -3 z" style="stroke-width: 0.33;"></path></svg>South</li><li value="sw" role="option" aria-selected="false"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="m 10.633,13.834247 -6.99459,6.994163 0.921569,0.921531 -2.310036,5.9e-5 -1.1e-5,-2.310013 0.921778,0.921742 6.9946,-6.994173 z M 13,6.666 v 2 h -1 v -2 z M 20.667,11 v 1 h -2 v -1 z m -3.333,0 v 1 h -2 V 11 Z M 14,1 V 2 H 11 V 1 Z m 9,9 v 3 H 22 V 10 Z M 13,3.333 v 2 h -1 v -2 z M 14,10 v 3 h -3 v -3 z m -1,1 h -1 v 1 h 1 z M 24,0 V 24 H 0 V 0 Z M 23,1 H 1 v 22 h 22 z" style="stroke-width: 0.33;"></path></svg>Southwest</li><li value="w" role="option" aria-selected="false"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M 10.232048,18.717 3.70167,20.839166 3.298966,19.599675 2.250179,21.657905 4.30841,22.706639 3.90561,21.466866 10.436,19.344697 Z m 0,-13.4343369 L 3.70167,3.1604974 3.298966,4.3999884 2.250179,2.3417578 4.30841,1.2930239 3.90561,2.5327967 10.436,4.6549659 Z M 14,16 v 3 h -3 v -3 z m -1,1 h -1 v 1 h 1 z m 0,-4.334 v 2 h -1 v -2 z M 20.667,17 v 1 h -2 v -1 z m -3.333,0 v 1 h -2 v -1 z m 0,-11 v 1 h -2 V 6 Z m 3.333,1 V 6 h -2 V 7 Z M 13,9.333 v 2 h -1 v -2 z M 24,0 V 24 H 0 V 0 Z M 23,1 H 1 V 23 H 23 Z M 14,5 V 8 H 11 V 5 Z m -1,1 h -1 v 1 h 1 z M 23,5 V 8 H 22 V 5 Z m 0,11 v 3 h -1 v -3 z" style="stroke-width: 0.33;"></path></svg>West</li><li value="nw" role="option" aria-selected="false"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M 10.633,10.165753 3.63841,3.17159 4.559979,2.250059 2.249943,2.25 2.249932,4.560013 3.17171,3.638271 l 6.9946,6.994173 z M 13,17.334 v -2 h -1 v 2 z M 20.667,13 v -1 h -2 v 1 z m -3.333,0 v -1 h -2 v 1 z M 14,23 v -1 h -3 v 1 z m 9,-9 v -3 h -1 v 3 z m -10,6.667 v -2 h -1 v 2 z M 14,14 v -3 h -3 v 3 z m -1,-1 h -1 v -1 h 1 z M 24,24 V 0 H 0 V 24 Z M 23,23 H 1 V 1 h 22 z" style="stroke-width: 0.33;"></path></svg>Northwest</li></ul></div><a download="Karius_und_Baktus.jpg" href="/media/finder_demo/2b/94/2b947dbf-d0c6-4a73-9633-10b4db5ce155/Karius_und_Baktus.jpg"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M4 19H20V12H22V20C22 20.5523 21.5523 21 21 21H3C2.44772 21 2 20.5523 2 20V12H4V19ZM14 9H19L12 16L5 9H10V3H14V9Z"></path></svg>Download</a><button type="button"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M 3,3 C 2.4477,3 2,3.44772 2,4 v 7 H 4 V 5 h 16 v 14 h -6 v 2 h 7 c 0.55228,0 1,-0.4477 1,-1 V 4 C 22,3.44772 21.55228,3 21,3 Z m 0,10 c -0.5523,0 -1,0.4477 -1,1 v 6 c 0,0.5523 0.4477,1 1,1 h 8 c 0.5523,0 1,-0.4477 1,-1 v -6 c 0,-0.5523 -0.4477,-1 -1,-1 z m 1,2 h 6 v 4 H 4 Z m 8.5,-8 2.04289,2.04311 -2.24999,2.24979 1.4142,1.4142 2.24979,-2.25 L 18,12.5 V 7 Z"></path></svg>View Original</button><button type="button"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M4 19H20V12H22V20C22 20.5523 21.5523 21 21 21H3C2.44772 21 2 20.5523 2 20V12H4V19ZM14 9V15H10V9H5L12 2L19 9H14Z"></path></svg>Replace File</button><input accept="image/jpeg" type="file" name="replaceFile"></div></div>


def test_get_raw_image_admin(admin_client, admin_user, ambit):
    from finder.contrib.image.models import ImageFileModel

    image = Image.new('RGB', (300, 300))
    draw = ImageDraw.Draw(image)
    color = (128, 128, 128)
    draw.rectangle([0, 0, 300, 300], fill=color)
    buffer = BytesIO()
    image.save(buffer, format='TIFF')
    buffer.seek(0)
    uploaded_file = SimpleUploadedFile('test_image.tiff', buffer.read(), content_type='image/tiff')
    raw_image_file = ImageFileModel.objects.create_from_upload(
        ambit,
        uploaded_file,
        folder=ambit.root_folder,
        owner=admin_user,
    )
    admin_url = f'/admin/finder/{ambit.slug}/{raw_image_file.id}'
    response = admin_client.get(admin_url)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.title.string == f"{raw_image_file.name} | Change image file model | Django site admin"
    # file_details = soup.find('div', class_='file-details')
    # assert file_details is not None
    # assert file_details.find('h2').string == image_file.name
    # assert file_details.find('img')['src'] == image_file.file.url
