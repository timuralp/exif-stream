import fractions
import struct


class ExifTag(object):
    TAG_DESCRIPTIONS = {
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
        0x829a: 'Exposure time',
        0x829d: 'F number',
        0x9003: 'Image taken date/time',
        0x9004: 'Image digitized date/time',
        0x9201: 'Shutter speed',
        0x9202: 'Aperture',
        0x9203: 'Brightness value',
        0x9204: 'Exposure bias value',
        0x9205: 'Max aperture value',
        0x920a: 'Focal length',
        0x9286: 'User comment tag',
        0xa420: 'Image ID',
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
            if elements == 1:
                return ret[0]
            return ret
        elif self._fmt == 4:
            elements = len(self._data)/4
            ret = struct.unpack(self._endian + 'I'*elements, self._data)
            if elements == 1:
                return ret[0]
            return ret
        elif self._fmt == 5 or self._fmt == 10:
            elements = len(self._data)/4
            if self._fmt == 5:
                item = 'I'
            else:
                item = 'i'
            data = struct.unpack(self._endian + 'I'*elements, self._data)
            results = []
            for i in range(0, elements/2):
                rational = fractions.Fraction(data[i], data[i+1])
                results.append(str(rational))
            if len(results) == 1:
                return results[0]
            return results
        elif self._fmt == 7:
            if self._tag == 0x9000:
                return self._data
            return struct.unpack('B'*len(self._data), self._data)
        else:
            return 'Format %d is not parsed' % self._fmt

    def __str__(self):
        descr = self.TAG_DESCRIPTIONS.get(self._tag,
                                          'Unknown tag (%x)' % self._tag)

        return "%s: %s" % (descr, str(self._tag_value()))

    __repr__ = __str__
