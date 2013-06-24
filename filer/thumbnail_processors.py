#-*- coding: utf-8 -*-
import re
try:
    from PIL import Image
    from PIL import ImageDraw
except ImportError:
    try:
        import Image
        import ImageDraw
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")
from easy_thumbnails import processors
from filer.settings import FILER_SUBJECT_LOCATION_IMAGE_DEBUG, FILER_WHITESPACE_COLOR

RE_SUBJECT_LOCATION = re.compile(r'^(\d+),(\d+)$')


def normalize_subject_location(subject_location):
    if subject_location:
        if isinstance(subject_location, basestring):
            m = RE_SUBJECT_LOCATION.match(subject_location)
            if m:
                return (int(m.group(1)), int(m.group(2)))
        else:
            try:
                return (int(subject_location[0]), int(subject_location[1]))
            except (TypeError, ValueError):
                pass
    return False


def scale_and_crop_with_subject_location(im, size, subject_location=False,
                                         crop=False, upscale=False, **kwargs):
    """
    Like ``easy_thumbnails.processors.scale_and_crop``, but will use the
    coordinates in ``subject_location`` to make sure that that part of the
    image is in the center or at least somewhere on the cropped image.
    Please not that this does *not* work correctly if the image has been
    resized by a previous processor (e.g ``autocrop``).

    ``crop`` needs to be set for this to work, but any special cropping
    parameters will be ignored.
    """
    subject_location = normalize_subject_location(subject_location)
    if not (subject_location and crop):
        # use the normal scale_and_crop
        return processors.scale_and_crop(im, size, crop=crop,
                                         upscale=upscale, **kwargs)

    # for here on we have a subject_location and cropping is on

    # --snip-- this is a copy and paste of the first few
    #          lines of ``scale_and_crop``
    source_x, source_y = [float(v) for v in im.size]
    target_x, target_y = [float(v) for v in size]

    if crop or not target_x or not target_y:
        scale = max(target_x / source_x, target_y / source_y)
    else:
        scale = min(target_x / source_x, target_y / source_y)

    # Handle one-dimensional targets.
    if not target_x:
        target_x = source_x * scale
    elif not target_y:
        target_y = source_y * scale

    if scale < 1.0 or (scale > 1.0 and upscale):
        im = im.resize((int(source_x * scale), int(source_y * scale)),
                       resample=Image.ANTIALIAS)
    # --endsnip-- begin real code

    # ===============================
    # subject location aware cropping
    # ===============================
    # res_x, res_y: the resolution of the possibly already resized image
    res_x, res_y = [float(v) for v in im.size]

    # subj_x, subj_y: the position of the subject (maybe already re-scaled)
    subj_x = res_x * float(subject_location[0]) / source_x
    subj_y = res_y * float(subject_location[1]) / source_y
    ex = (res_x - min(res_x, target_x)) / 2
    ey = (res_y - min(res_y, target_y)) / 2
    fx, fy = res_x - ex, res_y - ey

    # box_width, box_height: dimensions of the target image
    box_width, box_height = fx - ex, fy - ey

    # try putting the box in the center around the subject point
    # (this will be partially outside of the image in most cases)
    tex, tey = subj_x - (box_width / 2), subj_y - (box_height / 2)
    tfx, tfy = subj_x + (box_width / 2), subj_y + (box_height / 2)
    if tex < 0:
        # its out of the img to the left, move both to the right until tex is 0
        tfx = tfx - tex  # tex is negative!
        tex = 0
    elif tfx > res_x:
        # its out of the img to the right
        tex = tex - (tfx - res_x)
        tfx = res_x

    if tey < 0:
        # its out of the img to the top, move both to the bottom until tey is 0
        tfy = tfy - tey  # tey is negative!)
        tey = 0
    elif tfy > res_y:
        # its out of the img to the bottom
        tey = tey - (tfy - res_y)
        tfy = res_y
    if ex or ey:
        crop_box = ((int(tex), int(tey), int(tfx), int(tfy)))
        if FILER_SUBJECT_LOCATION_IMAGE_DEBUG:
            # draw elipse on focal point for Debugging
            draw = ImageDraw.Draw(im)
            esize = 10
            draw.ellipse(((subj_x - esize, subj_y - esize),
                          (subj_x + esize, subj_y + esize)), outline="#FF0000")
        im = im.crop(crop_box)
    return im


def whitespace(image, size, whitespace=False, whitespace_color=None, **kwargs):
    if not whitespace:
        return image

    if whitespace_color is None:
        whitespace_color = FILER_WHITESPACE_COLOR
    if whitespace_color is None:
        whitespace_color = '#fff'

    old_image = image
    source_x, source_y = image.size
    target_x, target_y = size

    image = Image.new('RGBA', (target_x, target_y), whitespace_color)
    if source_x < target_x and source_y < target_y:  # whitespace all around
        image.paste(old_image, ((target_x-source_x)/2, (target_y-source_y)/2))
    elif source_x < target_x:  # whitespace on top and bottom only
        image.paste(old_image, ((target_x-source_x)/2, 0))
    elif source_y < target_y:  # whitespace on sides only
        image.paste(old_image, (0, (target_y-source_y)/2))
    else:  # no whitespace needed
        image = old_image

    return image