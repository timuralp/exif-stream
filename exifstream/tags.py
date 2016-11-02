import fractions
import struct


class ExifTag(object):
    TAG_DESCRIPTIONS = {
        0x0: 'GPS version ID',
        0x1: 'GPS latitude reference',
        0x2: 'GPS latitude',
        0x3: 'GPS longitude reference',
        0x4: 'GPS longitude',
        0x5: 'GPS altitude reference',
        0x6: 'GPS altitude',
        0x7: 'GPS time stamp',
        0xc: 'GPS speed units',
        0xd: 'GPS speed',
        0x10: 'GPS measurement mode',
        0x11: 'GPS image direction',
        0x17: 'GPS reference for destination point bearing',
        0x18: 'GPS bearing to the destination point',
        0x1d: 'GPS date',
        0x100: 'Image width',
        0x101: 'Image height',
        0x112: 'Orientation',
        0x128: 'Resolution unit',
        0x213: 'YCbCrPositioning',
        0x10f: 'Make',
        0x110: 'Model',
        0x11a: 'XResolution',
        0x11b: 'YResolution',
        0x131: 'Software',
        0x132: 'Date/Time',
        0x8822: 'Exposure program',
        0x8827: 'ISOSpeedRatings',
        0x9000: 'EXIF version',
        0x9101: 'Component configuration',
        0x9207: 'Metering mode',
        0x9208: 'Light source',
        0x9209: 'Flash',
        0xa000: 'FlashPix version',
        0xa001: 'ColorSpace',
        0xa002: 'Exif Image width',
        0xa003: 'Exif Image height',
        0xa005: 'Exif interoperability offset',
        0xa217: 'Sensing mode',
        0xa301: 'Scene type',
        0xa402: 'Exposure mode',
        0xa403: 'White balance',
        0xa405: 'Focal length in 35mm film',
        0xa406: 'Scene capture type',
        0xa432: 'Lens specification',
        0xa433: 'Lens make',
        0xa434: 'Lens model',
        0x829a: 'Exposure time',
        0x829d: 'F number',
        0x9003: 'Image taken date/time',
        0x9004: 'Image digitized date/time',
        0x9201: 'Shutter speed',
        0x9202: 'Aperture',
        0x9203: 'Brightness value',
        0x9204: 'Exposure bias value',
        0x9205: 'Max aperture value',
        0x9214: 'Subject location',
        0x920a: 'Focal length',
        0x9286: 'User comment tag',
        0xa420: 'Image ID',
        0x8825: 'GPS IFD',
        0x927c: 'Maker note',
    }

    def __init__(self, tag, fmt, data, endian):
        self._tag = tag
        self._fmt = fmt
        self._data = data
        self._endian = endian

    def _tag_value(self):
        if self._fmt == 2:
            # Strip off the null terminator
            return self._data[0:-1]
        elif self._fmt == 3:
            elements = len(self._data)/2
            ret = struct.unpack(self._endian + 'H'*elements, self._data)
            return ' '.join(map(str, ret))
        elif self._fmt == 4:
            elements = len(self._data)/4
            ret = struct.unpack(self._endian + 'I'*elements, self._data)
            return ' '.join(map(str, ret))
        elif self._fmt == 5 or self._fmt == 10:
            elements = len(self._data)/4
            if self._fmt == 5:
                item = 'I'
            else:
                item = 'i'
            data = struct.unpack(self._endian + 'I'*elements, self._data)
            results = []
            for i in range(0, elements/2):
                rational = fractions.Fraction(data[i*2], data[i*2 + 1])
                results.append(rational)
            if self._tag == 0x6:
                return str(results[0]) + ' m'
            # Parse the GPS Latitude/Longitude string correctly
            if self._tag == 0x2 or self._tag == 0x4:
                seconds = results[2].numerator*1.0/results[2].denominator
                return str(results[0]) + ' ' + str(results[1]) + "'" +\
                    str(seconds) + u'"'
            # GPS TimeStamp is also three rationals
            if self._tag == 0x7:
                return ':'.join(map(str, results))
            return ' '.join(map(str, results))
        elif self._fmt == 7:
            if self._tag == 0x9000:
                return self._data
            return struct.unpack('B'*len(self._data), self._data)
        elif self._fmt == 1 and self._tag == 0x5:
            flag = struct.unpack('B', self._data)
            return 'Above sea level' if self._data else 'Below sea level'
        else:
            return 'Format %d is not parsed' % self._fmt

    def tag(self):
        return self.TAG_DESCRIPTIONS.get(self._tag,
                                         'Unknown tag (%x)' % self._tag)

    def value(self):
        return str(self._tag_value())

    def __str__(self):
        return "%s: %s" % (self.tag(), unicode(self._tag_value()))

    __repr__ = __str__
