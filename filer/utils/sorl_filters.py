try:
    import Image
    import ImageColor
    import ImageFile
    import ImageFilter
    import ImageEnhance
    import ImageDraw
    import ExifTags
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageColor
        from PIL import ImageFile
        from PIL import ImageFilter
        from PIL import ImageEnhance
        from PIL import ImageDraw
        from PIL import ExifTags
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")
from filer.utils.pil_exif import get_exif, get_subject_location
        
def scale_and_crop(im, requested_size, opts, subject_location=None):
    # x, y: original image size
    x, y   = [float(v) for v in im.size]
    xr, yr = [float(v) for v in requested_size]
    
    # we need to extract exif data now, because after the first transition
    # the exif info is lost:
    exif_data = get_exif(im)
    
    if 'crop' in opts or 'max' in opts:
        r = max(xr/x, yr/y)
    else:
        r = min(xr/x, yr/y)
    if r < 1.0 or (r > 1.0 and 'upscale' in opts):
        im = im.resize((int(x*r), int(y*r)), resample=Image.ANTIALIAS)
        
    if 'crop' in opts:
        if not subject_location and exif_data:
            subject_location = get_subject_location(exif_data)
        if not subject_location:
            # default crop implementation
            # x, y: re-read here, because 'crop'/'upscale' may have changed them
            x, y   = [float(v) for v in im.size]
            ex, ey = (x-min(x, xr))/2, (y-min(y, yr))/2
            if ex or ey:
                im = im.crop((int(ex), int(ey), int(x-ex), int(y-ey)))
        else:
            # subject location aware cropping
            # res_x, res_y: the resolution of the possibly already resized image
            res_x, res_y   = [float(v) for v in im.size]
            # subj_x, subj_y: the position of the subject
            # better than this because of rounding issues: 
            # subj_x = res_x/(x/float(subject_location[0]))
            # subj_y = res_y/(y/float(subject_location[1]))
            subj_x = res_x*float(subject_location[0])/x
            subj_y = res_y*float(subject_location[1])/y   
            ex, ey = (res_x-min(res_x, xr))/2, (res_y-min(res_y, yr))/2
            fx, fy = res_x-ex, res_y-ey
            # get the dimensions of the resulting box
            box_width, box_height = fx - ex, fy - ey
            # try putting the box in the center around the subject point
            # (this will be outside of the image in most cases"
            tex, tey = subj_x-(box_width/2), subj_y-(box_height/2)
            tfx, tfy = subj_x+(box_width/2), subj_y+(box_height/2)
            if tex < 0:
                # its out of the img to the left, move both to the right until tex is 0
                tfx = tfx-tex # tex is negative!)
                tex = 0
            elif tfx > res_x:
                # its out of the img to rhe right
                tex = tex-(tfx-res_x)
                tfx = res_x
            
            if tey < 0:
                # its out of the img to the top, move both to the bottom until tey is 0
                tfy = tfy-tey # tey is negative!)
                tey = 0
            elif tfy > res_y:
                # its out of the img to rhe bottom
                tey = tey-(tfy-res_y)
                tfy = res_y
            if ex or ey:
                crop_box = ((int(tex), int(tey), int(tfx), int(tfy)))
                # draw elipse on focal point for Debugging
                #draw = ImageDraw.Draw(im)
                #esize = 10
                #draw.ellipse( ( (subj_x-esize, subj_y-esize), (subj_x+esize, subj_y+esize)), outline="#FF0000" )
                im = im.crop(crop_box)
    return im
scale_and_crop.valid_options = ('crop', 'upscale', 'max')