import re
import types
from django.template import Library, Node, VariableDoesNotExist, \
     TemplateSyntaxError

register = Library()

RE_DIMENSIONS = re.compile(r'(\d+)x(\d+)$')


def filer_video(source, video_dimensions=None):
    """
    Creates HTML5 video tag with the alternative video formats and fallback to 
    flash if that format is available.
    
    Tag Syntax
    
        {% filer_video [source] [dimensions] %}
    
    *source* must be a Django Filer video object
    
    *dimensions* is the display width and height and can be a string with 
     ``[width]x[height]`` (for example ``{% filer_video obj 320x240 %}``) or 
     a tuple variable with two integers. If no display dimensions are given 
     the movie dimensions are used.
    """
    tag_syntax_error = False
    if video_dimensions:
        if type(video_dimensions) == types.TupleType:
            if len(video_dimensions) != 2:
                tag_syntax_error = True
        else:
            match = RE_DIMENSIONS.match(video_dimensions)
            if not match or len(match.groups()) != 2:
                tag_syntax_error = True
            else:
                dimensions = map(int, match.groups())
    else:
        try:
            dimensions = (source.width, source.height)
        except:
            tag_syntax_error
            
    if tag_syntax_error:
        raise TemplateSyntaxError("Invalid syntax. Expected "
            "'{%% %s source [dimensions] %%}'" % tag)
    return {'video': source, 'dimensions': dimensions}


register.inclusion_tag('filer/video.html')(filer_video)