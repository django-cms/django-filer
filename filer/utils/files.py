import os

from filer.utils.zip import unzip

def generic_handle_file(file, original_filename):
    """
    Handels a file, regardless if a package or a single file and returns 
    a list of files. can recursively unpack packages.
    """
    #print "entering generic_handle_file(file=%s, original_filename=%s)" % (file, original_filename)
    files = []
    filetype = os.path.splitext(original_filename)[1].lower()
    #print filetype
    if filetype=='.zip':
        unpacked_files = unzip(file)
        for ufile, ufilename in unpacked_files:
            files += generic_handle_file(ufile, ufilename)
    else:
        files.append( (file,original_filename) )
    #print "result of generic_handle_file: ", files
    return files