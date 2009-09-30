"""
pexif is a module which allows you to view and modify meta-data in
JPEG/JFIF/EXIF files.

The main way to use this is to create an instance of the JpegFile class.
This should be done using one of the static factory methods fromFile,
fromString or fromFd.

After manipulating the object you can then write it out using one of the
writeFile, writeString or writeFd methods.

The get_exif() method on JpegFile returns the ExifSegment if one exists.

Example:

jpeg = pexif.JpegFile.fromFile("foo.jpg")
exif = jpeg.get_exif()
....
jpeg.writeFile("new.jpg")

For photos that don't currently have an exef segment you can specify
an argument which will create the exef segment if it doesn't exist.

Example:

jpeg = pexif.JpegFile.fromFile("foo.jpg")
exif = jpeg.get_exif(create=True)
....
jpeg.writeFile("new.jpg")

The JpegFile class handles file that are formatted in something
approach the JPEG specification (ISO/IEC 10918-1) Annex B 'Compressed
Data Formats', and JFIF and EXIF standard.

In particular, the way a 'jpeg' file is treated by pexif is that
a JPEG file is made of a series of segments followed by the image
data. In particular it should look something like:

[ SOI | <arbitrary segments> | SOS | image data | EOI ]

So, the library expects a Start-of-Image marker, followed
by an arbitrary number of segment (assuming that a segment
has the format:

[ <0xFF> <segment-id> <size-byte0> <size-byte1> <data> ]

and that there are no gaps between segments.

The last segment must be the Start-of-Scan header, and the library
assumes that following Start-of-Scan comes the image data, finally
followed by the End-of-Image marker.

This is probably not sufficient to handle arbitrary files conforming
to the JPEG specs, but it should handle files that conform to
JFIF or EXIF, as well as files that conform to neither but
have both JFIF and EXIF application segment (which is the majority
of files in existence!). 

When writing out files all segment will be written out in the order
in which they were read. Any 'unknown' segment will be written out
as is. Note: This may or may not corrupt the data. If the segment
format relies on absolute references then this library may still
corrupt that segment!


Can have a JpegFile in two modes: Read Only and Read Write.

Read Only mode: trying to access missing elements will result in
an AttributeError.

Read Write mode: trying to access missing elements will automatically
create them.

E.g: 

img.exif.primary.<tagname>
             .geo
             .interop
             .exif.<tagname>
             .exif.makernote.<tagname>
               
        .thumbnail
img.flashpix.<...>
img.jfif.<tagname>
img.xmp

E.g: 

try:
 print img.exif.tiff.exif.FocalLength
except AttributeError:
 print "No Focal Length data"

"""

import StringIO
import sys
from struct import unpack, pack

MAX_HEADER_SIZE = 64 * 1024
DELIM = 0xff
EOI = 0xd9
SOI_MARKER = chr(DELIM) + '\xd8'
EOI_MARKER = chr(DELIM) + '\xd9'

EXIF_OFFSET = 0x8769
GPSIFD = 0x8825

TIFF_OFFSET = 6
TIFF_TAG = 0x2a

DEBUG = 0

def debug(*debug_string):
    """Used for print style debugging. Enable by setting the global
    DEBUG to 1."""
    if DEBUG:
        for each in debug_string:
            print each,
        print

class DefaultSegment:
    """DefaultSegment represents a particluar segment of a JPEG file.
    This class is instantiated by JpegFile when parsing Jpeg files
    and is not intended to be used directly by the programmer. This
    base class is used as a default which doesn't know about the internal
    structure of the segment. Other classes subclass this to provide
    extra information about a particular segment.
    """
    
    def __init__(self, marker, fd, data, mode):
        """The constructor for DefaultSegment takes the marker which
        identifies the segments, a file object which is currently positioned
        at the end of the segment. This allows any subclasses to potentially
        extract extra data from the stream. Data contains the contents of the
        segment."""
        self.marker = marker
        self.data = data
        self.mode = mode
        self.fd = fd
        assert mode in ["rw", "ro"]
        if not self.data is None:
            self.parse_data(data)

    class InvalidSegment(Exception):
        """This exception may be raised by sub-classes in cases when they
        can't correctly identify the segment."""
        pass

    def write(self, fd):
        """This method is called by JpegFile when writing out the file. It
        must write out any data in the segment. This shouldn't in general be
        overloaded by subclasses, they should instead override the get_data()
        method."""
        fd.write('\xff')
        fd.write(pack('B', self.marker))
        data = self.get_data()
        fd.write(pack('>H', len(data) + 2))
        fd.write(data)

    def get_data(self):
        """This method is called by write to generate the data for this segment.
        It should be overloaded by subclasses."""
        return self.data

    def parse_data(self, data):
        """This method is called be init to parse any data for the segment. It
        should be overloaded by subclasses rather than overloading __init__"""
        pass

    def dump(self, fd):
        """This is called by JpegFile.dump() to output a human readable
        representation of the segment. Subclasses should overload this to provide
        extra information."""
        print >> fd, " Section: [%5s] Size: %6d" % \
              (jpeg_markers[self.marker][0], len(self.data))

class StartOfScanSegment(DefaultSegment):
    """The StartOfScan segment needs to be treated specially as the actual
    image data directly follows this segment, and that data is not included
    in the size as reported in the segment header. This instances of this class
    are created by JpegFile and it should not be subclassed.
    """
    def __init__(self, marker, fd, data, mode):
        DefaultSegment.__init__(self, marker, fd, data, mode)

        # For SOS we also pull out the actual data
        img_data = fd.read()
        # -2 accounts for the EOI marker at the end of the file
        self.img_data = img_data[:-2]
        fd.seek(-2, 1)

    def write(self, fd):
        """Write segment data to a given file object"""
        DefaultSegment.write(self, fd)
        fd.write(self.img_data)

    def dump(self, fd):
        """Dump as ascii readable data to a given file object"""
        print >> fd, " Section: [  SOS] Size: %6d Image data size: %6d" % \
              (len(self.data), len(self.img_data))

class ExifType:
    """The ExifType class encapsulates the data types used
    in the Exif spec. These should really be called TIFF types
    probably. This could be replaced by named tuples in python 2.6."""
    lookup = {}

    def __init__(self, type_id, name, size):
        """Create an ExifType with a given name, size and type_id"""
        self.id = type_id
        self.name = name
        self.size = size
        ExifType.lookup[type_id] = self

BYTE = ExifType(1, "byte", 1).id
ASCII = ExifType(2, "ascii", 1).id
SHORT = ExifType(3, "short", 2).id
LONG = ExifType(4, "long", 4).id
RATIONAL = ExifType(5, "rational", 8).id
UNDEFINED = ExifType(7, "undefined", 1).id
SLONG = ExifType(9, "slong", 4).id
SRATIONAL = ExifType(10, "srational", 8).id

def exif_type_size(exif_type):
    """Return the size of a type"""
    return ExifType.lookup.get(exif_type).size

class Rational:
    """A simple fraction class. Python 2.6 could use the inbuilt Fraction class."""

    def __init__(self, num, den):
        """Create a number fraction num/den."""
        self.num = num
        self.den = den

    def __repr__(self):
        """Return a string representation of the fraction."""
        return "%s / %s" % (self.num, self.den)

    def as_tuple(self):
        """Return the fraction a numerator, denominator tuple."""
        return (self.num, self.den)

class IfdData:
    """Base class for IFD"""
    
    name = "Generic Ifd"
    tags = {}
    embedded_tags = {}

    def special_handler(self, tag, data):
        """special_handler method can be over-ridden by subclasses
        to specially handle the conversion of tags from raw format
        into Python data types."""
        pass

    def ifd_handler(self, data):
        """ifd_handler method can be over-ridden by subclasses to
        specially handle conversion of the Ifd as a whole into a
        suitable python representation."""
        pass

    def extra_ifd_data(self, offset):
        """extra_ifd_data method can be over-ridden by subclasses
        to specially handle conversion of the Python Ifd representation
        back into a byte stream."""
        return ""


    def has_key(self, key):
        return self[key] != None

    def __setattr__(self, name, value):
        for key, entry in self.tags.items():
            if entry[1] == name:
                self[key] = value
        self.__dict__[name] = value

    def __delattr__(self, name):
        for key, entry in self.tags.items():
            if entry[1] == name:
                del self[key]
        del self.__dict__[name]

    def __getattr__(self, name):
        for key, entry in self.tags.items():
            if entry[1] == name:
                x = self[key]
                if x is None:
                    raise AttributeError
                return x
        for key, entry in self.embedded_tags.items():
            if entry[0] == name:
                if self.has_key(key):
                    return self[key]
                else:
                    if self.mode == "rw":
                        new = entry[1](self.e, 0, "rw", self.exif_file)
                        self[key] = new
                        return new
                    else:
                        raise AttributeError
        raise AttributeError, "%s not found.. %s" % (name, self.embedded_tags)

    def __getitem__(self, key):
        if type(key) == type(""):
            try:
                return self.__getattr__(key)
            except AttributeError:
                return None
        for entry in self.entries:
            if key == entry[0]:
                if entry[1] == ASCII and not entry[2] is None:
                    return entry[2].strip('\0')
                else:
                    return entry[2]
        return None

    def __delitem__(self, key):
        if type(key) == type(""):
            try:
                return self.__delattr__(key)
            except AttributeError:
                return None
        for entry in self.entries:
            if key == entry[0]:
                self.entries.remove(entry)

    def __setitem__(self, key, value):
        if type(key) == type(""):
            return self.__setattr__(key, value)
        found = 0
        if len(self.tags[key]) < 3:
            raise Exception("Error: Tags aren't set up correctly, should have tag type.")
        if self.tags[key][2] == ASCII:
            if not value is None and not value.endswith('\0'):
                value = value + '\0'
        for i in range(len(self.entries)):
            if key == self.entries[i][0]:
                found = 1
                entry = list(self.entries[i])
                if value is None:
                    del self.entries[i]
                else:
                    entry[2] = value
                    self.entries[i] = tuple(entry)
                break
        if not found:
            # Find type...
            # Not quite enough yet...
            self.entries.append((key, self.tags[key][2], value))
        return

    def __init__(self, e, offset, exif_file, mode, data = None):
        self.exif_file = exif_file
        self.mode = mode
        self.e = e
        self.entries = []
        if data is None:
            return
        num_entries = unpack(e + 'H', data[offset:offset+2])[0]
        next = unpack(e + "I", data[offset+2+12*num_entries:
                                    offset+2+12*num_entries+4])[0]
        debug("OFFSET %s - %s" % (offset, next))
        
        for i in range(num_entries):
            start = (i * 12) + 2 + offset
            debug("START: ", start)
            entry = unpack(e + "HHII", data[start:start+12])
            tag, exif_type, components, the_data = entry

            debug("%s %s %s %s %s" % (hex(tag), exif_type,
                                      exif_type_size(exif_type), components,
                                      the_data))
            byte_size = exif_type_size(exif_type) * components


            if tag in self.embedded_tags:
                actual_data = self.embedded_tags[tag][1](e, the_data,
                                                         exif_file, self.mode, data)
            else:
                if byte_size > 4:
                    debug(" ...offset %s" % the_data)
                    the_data = data[the_data:the_data+byte_size]
                else:
                    the_data = data[start+8:start+8+byte_size]

                if exif_type == BYTE or exif_type == UNDEFINED:
                    actual_data = list(the_data)
                elif exif_type == ASCII:
                    if the_data[-1] != '\0':
                        actual_data = the_data + '\0'
                        #raise JpegFile.InvalidFile("ASCII tag '%s' not 
                        # NULL-terminated: %s [%s]" % (self.tags.get(tag, 
                        # (hex(tag), 0))[0], the_data, map(ord, the_data)))
                        #print "ASCII tag '%s' not NULL-terminated: 
                        # %s [%s]" % (self.tags.get(tag, (hex(tag), 0))[0], 
                        # the_data, map(ord, the_data))
                    actual_data = the_data
                elif exif_type == SHORT:
                    actual_data = list(unpack(e + ("H" * components), the_data))
                elif exif_type == LONG:
                    actual_data = list(unpack(e + ("I" * components), the_data))
                elif exif_type == SLONG:
                    actual_data = list(unpack(e + ("i" * components), the_data))
                elif exif_type == RATIONAL or exif_type == SRATIONAL:
                    if exif_type == RATIONAL: t = "II"
                    else: t = "ii"
                    actual_data = []
                    for i in range(components):
                        actual_data.append(Rational(*unpack(e + t,
                                                            the_data[i*8:
                                                                     i*8+8])))
                else:
                    raise "Can't handle this"

                if (byte_size > 4):
                    debug("%s" % actual_data)

                self.special_handler(tag, actual_data)
            entry = (tag, exif_type, actual_data)
            self.entries.append(entry)

            debug("%-40s %-10s %6d %s" % (self.tags.get(tag, (hex(tag), 0))[0],
                                          ExifType.lookup[exif_type],
                                          components, actual_data))
        self.ifd_handler(data)

    def isifd(self, other):
        """Return true if other is an IFD"""
        return issubclass(other.__class__, IfdData)

    def getdata(self, e, offset, last = 0):
        data_offset = offset+2+len(self.entries)*12+4
        output_data = ""

        out_entries = []

        # Add any specifc data for the particular type
        extra_data = self.extra_ifd_data(data_offset)
        data_offset += len(extra_data)
        output_data += extra_data

        for tag, exif_type, the_data in self.entries:
            magic_type = exif_type
            if (self.isifd(the_data)):
                debug("-> Magic..")
                sub_data, next_offset = the_data.getdata(e, data_offset, 1)
                the_data = [data_offset]
                debug("<- Magic", next_offset, data_offset, len(sub_data),
                      data_offset + len(sub_data))
                data_offset += len(sub_data)
                assert(next_offset == data_offset)
                output_data += sub_data
                magic_type = exif_type
                if exif_type != 4:
                    magic_components = len(sub_data)
                else:
                    magic_components = 1
                exif_type = 4 # LONG
                byte_size = 4
                components = 1
            else:
                magic_components = components = len(the_data)
                byte_size = exif_type_size(exif_type) * components
            
            if exif_type == BYTE or exif_type == UNDEFINED:
                actual_data = "".join(the_data)
            elif exif_type == ASCII:
                actual_data = the_data 
            elif exif_type == SHORT:
                actual_data = pack(e + ("H" * components), *the_data)
            elif exif_type == LONG:
                actual_data = pack(e + ("I" * components), *the_data)
            elif exif_type == SLONG:
                actual_data = pack(e + ("i" * components), *the_data)
            elif exif_type == RATIONAL or exif_type == SRATIONAL:
                if exif_type == RATIONAL: t = "II"
                else: t = "ii"
                actual_data = ""
                for i in range(components):
                    actual_data += pack(e + t, *the_data[i].as_tuple())
            else:
                raise "Can't handle this", exif_type
            if (byte_size) > 4:
                output_data += actual_data
                actual_data = pack(e + "I", data_offset) 
                data_offset += byte_size
            else:
                actual_data = actual_data + '\0' * (4 - len(actual_data))
            out_entries.append((tag, magic_type,
                                magic_components, actual_data))

        data = pack(e + 'H', len(self.entries))
        for entry in out_entries:
            data += pack(self.e + "HHI", *entry[:3])
            data += entry[3]

        next_offset = data_offset
        if last:
            data += pack(self.e + "I", 0)
        else:
            data += pack(self.e + "I", next_offset)
        data += output_data

        assert (next_offset == offset+len(data))

        return data, next_offset

    def dump(self, f, indent = ""):
        """Dump the IFD file"""
        print >> f, indent + "<--- %s start --->" % self.name
        for entry in self.entries:
            tag, exif_type, data = entry
            if exif_type == ASCII:
                data = data.strip('\0')
            if (self.isifd(data)):
                data.dump(f, indent + "    ")
            else:
                if data and len(data) == 1:
                    data = data[0]
                print >> f, indent + "  %-40s %s" % \
                      (self.tags.get(tag, (hex(tag), 0))[0], data)
        print >> f, indent + "<--- %s end --->" % self.name

class IfdInterop(IfdData):
    name = "Interop"
    tags = {
        # Interop stuff
        0x0001: ("Interoperability index", "InteroperabilityIndex"),
        0x0002: ("Interoperability version", "InteroperabilityVersion"),
        0x1000: ("Related image file format", "RelatedImageFileFormat"),
        0x1001: ("Related image file width", "RelatedImageFileWidth"),
        0x1002: ("Related image file length", "RelatedImageFileLength"),
        }

class CanonIFD(IfdData):
    tags = {
        0x0006: ("Image Type", "ImageType"),
        0x0007: ("Firmware Revision", "FirmwareRevision"),
        0x0008: ("Image Number", "ImageNumber"),
        0x0009: ("Owner Name", "OwnerName"),
        0x000c: ("Camera serial number", "SerialNumber"),
        0x000f: ("Customer functions", "CustomerFunctions")
        }
    name = "Canon"


class FujiIFD(IfdData):
    tags = {
        0x0000: ("Note version", "NoteVersion"),
        0x1000: ("Quality", "Quality"),
        0x1001: ("Sharpness", "Sharpness"),
        0x1002: ("White balance", "WhiteBalance"),
        0x1003: ("Color", "Color"),
        0x1004: ("Tone", "Tone"),
        0x1010: ("Flash mode", "FlashMode"),
        0x1011: ("Flash strength", "FlashStrength"),
        0x1020: ("Macro", "Macro"),
        0x1021: ("Focus mode", "FocusMode"),
        0x1030: ("Slow sync", "SlowSync"),
        0x1031: ("Picture mode", "PictureMode"),
        0x1100: ("Motor or bracket", "MotorOrBracket"),
        0x1101: ("Sequence number", "SequenceNumber"),
        0x1210: ("FinePix Color", "FinePixColor"),
        0x1300: ("Blur warning", "BlurWarning"),
        0x1301: ("Focus warning", "FocusWarning"),
        0x1302: ("AE warning", "AEWarning")
        }
    name = "FujiFilm"

    def getdata(self, e, offset, last = 0):
        pre_data = "FUJIFILM"
        pre_data += pack("<I", 12)
        data, next_offset = IfdData.getdata(self, e, 12, last)
        return pre_data + data, next_offset + offset


def ifd_maker_note(e, offset, exif_file, mode, data):
    """Factory function for creating MakeNote entries"""
    if exif_file.make == "Canon":
        # Canon maker note appears to always be in Little-Endian
        return CanonIFD('<', offset, exif_file, mode, data)
    elif exif_file.make == "FUJIFILM":
        # The FujiFILM maker note is special.
        # See http://www.ozhiker.com/electronics/pjmt/jpeg_info/fujifilm_mn.html

        # First it has an extra header
        header = data[offset:offset+8]
        # Which should be FUJIFILM
        if header != "FUJIFILM":
            raise JpegFile.InvalidFile("This is FujiFilm JPEG. " \
                                       "Expecting a makernote header "\
                                       "<FUJIFILM>. Got <%s>." % header)
        # The it has its own offset
        ifd_offset = unpack("<I", data[offset+8:offset+12])[0]
        # and it is always litte-endian
        e = "<"
        # and the data is referenced from the start the Ifd data, not the
        # TIFF file.
        ifd_data = data[offset:]
        return FujiIFD(e, ifd_offset, exif_file, mode, ifd_data)
    else:
        raise JpegFile.InvalidFile("Unknown maker: %s. Can't "\
                                   "currently handle this." % exif_file.make)
        

class IfdGPS(IfdData):
    name = "GPS"
    tags = {
        0x0: ("GPS tag version", "GPSVersionID", BYTE, 4),
        0x1: ("North or South Latitude", "GPSLatitudeRef", ASCII, 2),
        0x2: ("Latitude", "GPSLatitude", RATIONAL, 3),
        0x3: ("East or West Longitude", "GPSLongitudeRef", ASCII, 2),
        0x4: ("Longitude", "GPSLongitude", RATIONAL, 3),
        0x5: ("Altitude reference", "GPSAltitudeRef", BYTE, 1),
        0x6: ("Altitude", "GPSAltitude", RATIONAL, 1)
        }

    def __init__(self, e, offset, exif_file, mode, data = None):
        IfdData.__init__(self, e, offset, exif_file, mode, data)
        if data is None:
            self.GPSVersionID = ['\x02', '\x02', '\x00', '\x00']

class IfdExtendedEXIF(IfdData):
    tags = {
        # Exif IFD Attributes
        # A. Tags relating to version
        0x9000: ("Exif Version", "ExifVersion"),
        0xA000: ("Supported Flashpix version", "FlashpixVersion"),
        # B. Tag relating to Image Data Characteristics
        0xA001: ("Color Space Information", "ColorSpace"),
        # C. Tags relating to Image Configuration
        0x9101: ("Meaning of each component", "ComponentConfiguration"),
        0x9102: ("Image compression mode", "CompressedBitsPerPixel"),
        0xA002: ("Valid image width", "PixelXDimension"),
        0xA003: ("Valid image height", "PixelYDimension"),
        # D. Tags relatin to User informatio
        0x927c: ("Manufacturer notes", "MakerNote"),
        0x9286: ("User comments", "UserComment"),
        # E. Tag relating to related file information
        0xA004: ("Related audio file", "RelatedSoundFile"),
        # F. Tags relating to date and time
        0x9003: ("Date of original data generation", "DateTimeOriginal", ASCII),
        0x9004: ("Date of digital data generation", "DateTimeDigitized", ASCII),
        0x9290: ("DateTime subseconds", "SubSecTime"),
        0x9291: ("DateTime original subseconds", "SubSecTimeOriginal"),
        0x9292: ("DateTime digitized subseconds", "SubSecTimeDigitized"),
        # G. Tags relating to Picture taking conditions
        0x829a: ("Exposure Time", "ExposureTime"),
        0x829d: ("F Number", "FNumber"),
        0x8822: ("Exposure Program", "ExposureProgram"),    
        0x8824: ("Spectral Sensitivity", "SpectralSensitivity"),
        0x8827: ("ISO Speed Rating", "ISOSpeedRatings"),
        0x8829: ("Optoelectric conversion factor", "OECF"),
        0x9201: ("Shutter speed", "ShutterSpeedValue"),
        0x9202: ("Aperture", "ApertureValue"),
        0x9203: ("Brightness", "BrightnessValue"),
        0x9204: ("Exposure bias", "ExposureBiasValue"),
        0x9205: ("Maximum lens apeture", "MaxApertureValue"),
        0x9206: ("Subject Distance", "SubjectDistance"),
        0x9207: ("Metering mode", "MeteringMode"),
        0x9208: ("Light mode", "LightSource"),
        0x9209: ("Flash", "Flash"),
        0x920a: ("Lens focal length", "FocalLength"),
        0x9214: ("Subject area", "Subject area"),
        0xa20b: ("Flash energy", "FlashEnergy"),
        0xa20c: ("Spatial frequency results", "SpatialFrquencyResponse"),
        0xa20e: ("Focal plane X resolution", "FocalPlaneXResolution"),
        0xa20f: ("Focal plane Y resolution", "FocalPlaneYResolution"),
        0xa210: ("Focal plane resolution unit", "FocalPlaneResolutionUnit"),
        0xa214: ("Subject location", "SubjectLocation",SHORT),
        0xa215: ("Exposure index", "ExposureIndex"),
        0xa217: ("Sensing method", "SensingMethod"),
        0xa300: ("File source", "FileSource"),
        0xa301: ("Scene type", "SceneType"),
        0xa302: ("CFA pattern", "CFAPattern"),
        0xa401: ("Customer image processing", "CustomerRendered"),
        0xa402: ("Exposure mode", "ExposureMode"),
        0xa403: ("White balance", "WhiteBalance"),
        0xa404: ("Digital zoom ratio", "DigitalZoomRation"),
        0xa405: ("Focal length in 35mm film", "FocalLengthIn35mmFilm"),
        0xa406: ("Scene capture type", "SceneCaptureType"),
        0xa407: ("Gain control", "GainControl"),
        0xa40a: ("Sharpness", "Sharpness"),
        0xa40c: ("Subject distance range", "SubjectDistanceRange"),
        
        # H. Other tags
        0xa420: ("Unique image ID", "ImageUniqueID"),
        }
    embedded_tags = {
        0x927c: ("MakerNote", ifd_maker_note),
        }
    name = "Extended EXIF"

class IfdTIFF(IfdData):
    """
    """

    tags = {
        # Private Tags
        0x8769: ("Exif IFD Pointer", "ExifOffset", LONG), 
        0xA005: ("Interoparability IFD Pointer", "InteroparabilityIFD", LONG),
        0x8825: ("GPS Info IFD Pointer", "GPSIFD", LONG),
        # TIFF stuff used by EXIF

        # A. Tags relating to image data structure
        0x100: ("Image width", "ImageWidth", LONG),
        0x101: ("Image height", "ImageHeight", LONG),
        0x102: ("Number of bits per component", "BitsPerSample", SHORT),
        0x103: ("Compression Scheme", "Compression", SHORT),
        0x106: ("Pixel Composition", "PhotometricInterpretion", SHORT),
        0x112: ("Orientation of image", "Orientation", SHORT),
        0x115: ("Number of components", "SamplesPerPixel", SHORT),
        0x11c: ("Image data arrangement", "PlanarConfiguration", SHORT),
        0x212: ("Subsampling ration of Y to C", "YCbCrSubsampling", SHORT),
        0x213: ("Y and C positioning", "YCbCrCoefficients", SHORT),
        0x11a: ("X Resolution", "XResolution", RATIONAL),
        0x11b: ("Y Resolution", "YResolution", RATIONAL),
        0x128: ("Unit of X and Y resolution", "ResolutionUnit", SHORT),

        # B. Tags relating to recording offset
        0x111: ("Image data location", "StripOffsets", LONG),
        0x116: ("Number of rows per strip", "RowsPerStrip", LONG),
        0x117: ("Bytes per compressed strip", "StripByteCounts", LONG),
        0x201: ("Offset to JPEG SOI", "JPEGInterchangeFormat", LONG),
        0x202: ("Bytes of JPEG data", "JPEGInterchangeFormatLength", LONG),

        # C. Tags relating to image data characteristics

        # D. Other tags
        0x132: ("File change data and time", "DateTime", ASCII),
        0x10e: ("Image title", "ImageDescription", ASCII),
        0x10f: ("Camera Make", "Make", ASCII),
        0x110: ("Camera Model", "Model", ASCII),
        0x131: ("Camera Software", "Software", ASCII),
        0x13B: ("Artist", "Artist", ASCII),
        0x8298: ("Copyright holder", "Copyright", ASCII),
    }
    
    embedded_tags = {
        0xA005: ("Interoperability", IfdInterop), 
        EXIF_OFFSET: ("ExtendedEXIF", IfdExtendedEXIF),
        0x8825: ("GPS", IfdGPS),
        }

    name = "TIFF Ifd"

    def special_handler(self, tag, data):
        try:
            if self.tags[tag][1] == "Make":
                self.exif_file.make = data.strip('\0')
        except KeyError, e:
            pass

    def new_gps(self):
        if self.has_key(GPSIFD):
            raise ValueError, "Already have a GPS Ifd" 
        assert self.mode == "rw"
        gps = IfdGPS(self.e, 0, self.mode, self.exif_file)
        self[GPSIFD] = gps
        return gps

class IfdThumbnail(IfdTIFF):
    name = "Thumbnail"

    def ifd_handler(self, data):
        size = None
        offset = None
        for (tag, exif_type, val) in self.entries:
            if (tag == 0x201):
                offset = val[0]
            if (tag == 0x202):
                size = val[0]
        if size is None or offset is None:
            raise JpegFile.InvalidFile("Thumbnail doesn't have an offset "\
                                       "and/or size")
        self.jpeg_data = data[offset:offset+size]
        if len(self.jpeg_data) != size:
            raise JpegFile.InvalidFile("Not enough data for JPEG thumbnail."\
                                       "Wanted: %d got %d" %
                                       (size, len(self.jpeg_data)))

    def extra_ifd_data(self, offset):
        for i in range(len(self.entries)):
            entry = self.entries[i]
            if entry[0] == 0x201:
                # Print found field and updating
                new_entry = (entry[0], entry[1], [offset])
                self.entries[i] = new_entry
        return self.jpeg_data

class ExifSegment(DefaultSegment):
    """ExifSegment encapsulates the Exif data stored in a JpegFile. An
    ExifSegment contains two Image File Directories (IFDs). One is attribute
    information and the other is a thumbnail. This module doesn't provide
    any useful functions for manipulating the thumbnail, but does provide
    a get_attributes returns an AttributeIfd instances which allows you to
    manipulate the attributes in a Jpeg file."""

    def __init__(self, marker, fd, data, mode):
        self.ifds = []
        self.e = '<'
        self.tiff_endian = 'II'
        DefaultSegment.__init__(self, marker, fd, data, mode)
    
    def parse_data(self, data):
        """Overloads the DefaultSegment method to parse the data of
        this segment. Can raise InvalidFile if we don't get what we expect."""
        exif = unpack("6s", data[:6])[0]
        exif = exif.strip('\0')

        if (exif != "Exif"):
            raise self.InvalidSegment("Bad Exif Marker. Got <%s>, "\
                                       "expecting <Exif>" % exif)

        tiff_data = data[TIFF_OFFSET:]
        data = None # Don't need or want data for now on..
        
        self.tiff_endian = tiff_data[:2]
        if self.tiff_endian == "II":
            self.e = "<"
        elif self.tiff_endian == "MM":
            self.e = ">"
        else:
            raise JpegFile.InvalidFile("Bad TIFF endian header. Got <%s>, "
                                       "expecting <II> or <MM>" % 
                                       self.tiff_endian)

        tiff_tag, tiff_offset = unpack(self.e + 'HI', tiff_data[2:8])

        if (tiff_tag != TIFF_TAG):
            raise JpegFile.InvalidFile("Bad TIFF tag. Got <%x>, expecting "\
                                       "<%x>" % (tiff_tag, TIFF_TAG))

        # Ok, the header parse out OK. Now we parse the IFDs contained in
        # the APP1 header.
        
        # We use this loop, even though we can really only expect and support
        # two IFDs, the Attribute data and the Thumbnail data
        offset = tiff_offset
        count = 0

        while offset:
            count += 1
            num_entries = unpack(self.e + 'H', tiff_data[offset:offset+2])[0]
            start = 2 + offset + (num_entries*12)
            if (count == 1):
                ifd = IfdTIFF(self.e, offset, self, self.mode, tiff_data)
            elif (count == 2):
                ifd = IfdThumbnail(self.e, offset, self, self.mode, tiff_data)
            else:
                raise JpegFile.InvalidFile()
            self.ifds.append(ifd)

            # Get next offset
            offset = unpack(self.e + "I", tiff_data[start:start+4])[0]

    def dump(self, fd):
        print >> fd, " Section: [ EXIF] Size: %6d" % \
              (len(self.data))
        for ifd in self.ifds:
            ifd.dump(fd)

    def get_data(self):
        ifds_data = ""
        next_offset = 8
        for ifd in self.ifds:
            debug("OUT IFD")
            new_data, next_offset = ifd.getdata(self.e, next_offset,
                                                ifd == self.ifds[-1])
            ifds_data += new_data
            
        data = ""
        data += "Exif\0\0"
        data += self.tiff_endian
        data += pack(self.e + "HI", 42, 8)
        data += ifds_data
        
        return data

    def get_primary(self, create=False):
        """Return the attributes image file descriptor. If it doesn't
        exit return None, unless create is True in which case a new
        descriptor is created."""
        if len(self.ifds) > 0:
            return self.ifds[0]
        else:
            if create:
                assert self.mode == "rw"
                new_ifd = IfdTIFF(self.e, None, self, "rw")
                self.ifds.insert(0, new_ifd)
                return new_ifd
            else:
                return None

    def _get_property(self):
        if self.mode == "rw":
            return self.get_primary(True)
        else:
            primary = self.get_primary()
            if primary is None:
                raise AttributeError
            return primary

    primary = property(_get_property)

jpeg_markers = {
    0xc0: ("SOF0", []),
    0xc2: ("SOF2", []),
    0xc4: ("DHT", []),

    0xda: ("SOS", [StartOfScanSegment]),
    0xdb: ("DQT", []),
    0xdd: ("DRI", []),
    
    0xe0: ("APP0", []),
    0xe1: ("APP1", [ExifSegment]),
    0xe2: ("APP2", []),
    0xe3: ("APP3", []),
    0xe4: ("APP4", []),
    0xe5: ("APP5", []),
    0xe6: ("APP6", []),
    0xe7: ("APP7", []),
    0xe8: ("APP8", []),
    0xe9: ("APP9", []),
    0xea: ("APP10", []),
    0xeb: ("APP11", []),
    0xec: ("APP12", []),
    0xed: ("APP13", []),
    0xee: ("APP14", []),
    0xef: ("APP15", []),
    
    0xfe: ("COM", []),
    }

APP1 = 0xe1

class JpegFile:
    """JpegFile object. You should create this using one of the static methods
    fromFile, fromString or fromFd. The JpegFile object allows you to examine and
    modify the contents of the file. To write out the data use one of the methods
    writeFile, writeString or writeFd. To get an ASCII dump of the data in a file
    use the dump method."""
    
    def fromFile(filename, mode="rw"):
        """Return a new JpegFile object from a given filename."""
        return JpegFile(open(filename, "rb"), filename=filename, mode=mode)
    fromFile = staticmethod(fromFile)

    def fromString(str, mode="rw"):
        """Return a new JpegFile object taking data from a string."""
        return JpegFile(StringIO.StringIO(str), "from buffer", mode=mode)
    fromString = staticmethod(fromString)

    def fromFd(fd, mode="rw"):
        """Return a new JpegFile object taking data from a file object."""
        return JpegFile(fd, "fd <>", mode=mode)
    fromFd = staticmethod(fromFd)

    class InvalidFile(Exception):
        """This exception is raised if a given file is not able to be parsed."""
        pass

    class NoSection(Exception):
        """This exception is raised if a section is unable to be found."""
        pass
    
    def __init__(self, input, filename=None, mode="rw"):
        """JpegFile Constructor. input is a file object, and filename
        is a string used to name the file. (filename is used only for
        display functions).  You shouldn't use this function directly,
        but rather call one of the static methods fromFile, fromString
        or fromFd."""
        self.filename = filename
        self.mode = mode
        # input is the file descriptor
        soi_marker = input.read(len(SOI_MARKER))

        # The very first thing should be a start of image marker
        if (soi_marker != SOI_MARKER):
            raise self.InvalidFile("Error reading soi_marker. Got <%s> "\
                                   "should be <%s>" % (soi_marker, SOI_MARKER))

        # Now go through and find all the blocks of data
        segments = []
        while 1:
            head = input.read(2)
            delim, mark  =  unpack(">BB", head)
            if (delim != DELIM):
                raise self.InvalidFile("Error, expecting delmiter. "\
                                       "Got <%s> should be <%s>" %
                                       (delim, DELIM))
            if mark == EOI:
                # Hit end of image marker, game-over!
                break
            head2 = input.read(2)
            size = unpack(">H", head2)[0]
            data = input.read(size-2)
            possible_segment_classes = jpeg_markers[mark][1] + [DefaultSegment]
            # Try and find a valid segment class to handle
            # this data
            for segment_class in possible_segment_classes:
                try:
                    # Note: Segment class may modify the input file 
                    # descriptor. This is expected.
                    attempt = segment_class(mark, input, data, self.mode)
                    segments.append(attempt)
                    break
                except DefaultSegment.InvalidSegment:
                    # It wasn't this one so we try the next type.
                    # DefaultSegment will always work.
                    continue

        self._segments = segments

    def writeString(self):
        """Write the JpegFile out to a string. Returns a string."""
        f = StringIO.StringIO()
        self.writeFd(f)
        return f.getvalue()

    def writeFile(self, filename):
        """Write the JpegFile out to a file named filename."""
        output = open(filename, "wb")
        self.writeFd(output)

    def writeFd(self, output):
        """Write the JpegFile out on the file object output."""
        output.write(SOI_MARKER)
        for segment in self._segments:
            segment.write(output)
        output.write(EOI_MARKER)

    def dump(self, f = sys.stdout):
        """Write out ASCII representation of the file on a given file
        object. Output default to stdout."""
        print >> f, "<Dump of JPEG %s>" % self.filename
        for segment in self._segments:
            segment.dump(f)

    def get_exif(self, create=False):
        """get_exif returns a ExifSegment if one exists for this file.
        If the file does not have an exif segment and the create is
        false, then return None. If create is true, a new exif segment is
        added to the file and returned."""
        for segment in self._segments:
            if segment.__class__ == ExifSegment:
                return segment
        if create:
            return self.add_exif()
        else:
            return None

    def add_exif(self):
        """add_exif adds a new ExifSegment to a file, and returns
        it. When adding an EXIF segment is will add it at the start of
        the list of segments."""
        assert self.mode == "rw"
        new_segment = ExifSegment(APP1, None, None, "rw")
        self._segments.insert(0, new_segment)
        return new_segment


    def _get_exif(self):
        """Exif Attribute property"""
        if self.mode == "rw":
            return self.get_exif(True)
        else:
            exif = self.get_exif(False)
            if exif is None:
                raise AttributeError
            return exif

    exif = property(_get_exif)

    def get_geo(self):
        """Return a tuple of (latitude, longitude)."""
        def convert(x):
            (deg, min, sec) = x
            return (float(deg.num) / deg.den) +  \
                (1/60.0 * float(min.num) / min.den) + \
                (1/3600.0 * float(sec.num) / sec.den)
        if not self.exif.primary.has_key(GPSIFD):
            raise self.NoSection, "File %s doesn't have a GPS section." % \
                self.filename
            
        gps = self.exif.primary.GPS
        lat = convert(gps.GPSLatitude)
        lng = convert(gps.GPSLongitude)
        if gps.GPSLatitudeRef == "S":
            lat = -lat
        if gps.GPSLongitudeRef == "W":
            lng = -lng

        return lat, lng

    SEC_DEN = 50000000

    def _parse(val):
        sign = 1
        if val < 0:
            val  = -val
            sign = -1
            
        deg = int(val)
        other = (val - deg) * 60
        minutes = int(other)
        secs = (other - minutes) * 60
        secs = long(secs * JpegFile.SEC_DEN)
        return (sign, deg, minutes, secs)

    _parse = staticmethod(_parse)
        
    def set_geo(self, lat, lng):
        """Set the GeoLocation to a given lat and lng"""
        if self.mode != "rw":
            raise RWError

        gps = self.exif.primary.GPS

        sign, deg, min, sec = JpegFile._parse(lat)
        ref = "N"
        if sign < 0:
            ref = "S"

        gps.GPSLatitudeRef = ref
        gps.GPSLatitude = [Rational(deg, 1), Rational(min, 1),
                            Rational(sec, JpegFile.SEC_DEN)]

        sign, deg, min, sec = JpegFile._parse(lng)
        ref = "E"
        if sign < 0:
            ref = "W"
        gps.GPSLongitudeRef = ref
        gps.GPSLongitude = [Rational(deg, 1), Rational(min, 1),
                             Rational(sec, JpegFile.SEC_DEN)]

