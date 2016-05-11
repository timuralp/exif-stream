import struct
from .tags import ExifTag


class StreamProcessor(object):
    EXIF_HEADER = 'Exif\x00\x00'
    TIFF_HEADER_LEN = 8
    IFD_LEN = 12

    COMPONENT_SIZES = {
        1: 1,
        2: 1,
        3: 2,
        4: 4,
        5: 8,
        6: 1,
        7: 1,
        8: 2,
        9: 4,
        10: 8,
        11: 4,
        12: 8,
    }

    def __init__(self):
        self.buffer = ''
        self.tags = []
        self.state = None
        self.exif_marker_size = None
        self.marker_pos = 0
        self.tiff_alignment = None
        self.ifd_offsets = {}
        self.sub_ifd_offset = None
        self.next_ifd_offset = None
        self.file_offset = 0
        self.current_tag = None
        self.tiff_start = None

    def check_type(self, header_str):
        if header_str != b'\xFF\xD8':
            raise RuntimeError('Unknown format')

    def get_marker_type(self, data):
        if data[0] == b'\xFF':
            return data[1]
        else:
            raise RuntimeError('Unknown tag')

    def get_marker_size(self, data):
        # EXIF marker's size uncludes the two bytes storing the size
        return struct.unpack('>H', data[0:2])[0] - 2

    def unpack_tiff_data(self, fmt, data):
        return struct.unpack(self.tiff_alignment + fmt, data)

    def read_sized_length(self, data, length):
        if len(data) + len(self.buffer) < length:
            self.buffer += data
            return (None, None)
        if not self.buffer and len(data) >= length:
            result_str = data[:length]
        else:
            result_str = self.buffer + data[:length - len(self.buffer)]
        buffer_len = len(self.buffer)
        self.buffer = ''
        return (result_str, data[length - buffer_len:])

    def check_jpeg_start(self, data):
        header_str, data = self.read_sized_length(data, 2)
        if not header_str:
            return None
        self.check_type(header_str)
        self.state = 'exif marker'
        return data

    def handle_exif_marker(self, data):
        # we expect to read an EXIF tag now, which is 4 bytes:
        # \xFF + ID (1 byte) + 16 bit size
        exif_header, data = self.read_sized_length(data, 4)
        if not exif_header:
            return None
        marker_id = self.get_marker_type(exif_header)
        self.exif_marker_size = self.get_marker_size(exif_header[2:])
        self.state = 'exif marker data'
        return data

    def handle_non_exif_data(self, data):
        # We ignore the non-Exif markers (e.g. JFIF)
        if len(data) + self.marker_pos >= self.exif_marker_size:
            self.state = 'exif marker'
            self.marker_pos = 0
            return data[self.exif_marker_size - self.marker_pos:]
        self.marker_pos += len(data)
        return None

    def handle_exif_marker_data(self, data):
        if self.exif_marker_size < len(self.EXIF_HEADER):
            self.state = 'non-exif marker'
            return data
        for i in range(self.marker_pos, len(self.EXIF_HEADER)):
            if len(data) + self.marker_pos <= i:
                self.marker_pos = i
                return None
            if data[i - self.marker_pos] != self.EXIF_HEADER[i]:
                self.state = 'non-exif marker'
                return data
        self.state = 'tiff-data'
        read_exif_bytes = len(self.EXIF_HEADER) - self.marker_pos
        self.tiff_start = self.file_offset + read_exif_bytes
        self.marker_pos = 0
        return data[read_exif_bytes:]

    def handle_tiff_headers(self, data):
        if self.marker_pos < 2:
            # the first two bytes are the alignment
            align_str, data = self.read_sized_length(data, 2)
            if not align_str:
                return None
            if align_str == '\x49\x49':
                self.tiff_alignment = '<'
            elif align_str == '\x4d\x4d':
                self.tiff_alignment = '>'
            else:
                raise RuntimeError('Invalid alignment in the TIFF header')
            self.marker_pos = 2
        if self.marker_pos >= 2 and self.marker_pos < 4:
            tiff_check_str, data = self.read_sized_length(data, 2)
            if not tiff_check_str:
                return None
            read_tiff_mark = self.unpack_tiff_data('H', tiff_check_str)[0]
            if read_tiff_mark != 0x2a:
                raise RuntimeError('Invalid TIFF header')
            self.marker_pos = 4
        if self.marker_pos >= 4 and self.marker_pos < self.TIFF_HEADER_LEN:
            offset_str, data = self.read_sized_length(data, 4)
            if not offset_str:
                return None
            ifd_offset = self.unpack_tiff_data('I', offset_str)[0]
            self.ifd_skip_bytes = ifd_offset - self.TIFF_HEADER_LEN
            self.marker_pos = self.TIFF_HEADER_LEN
        if self.marker_pos == self.TIFF_HEADER_LEN:
            if len(data) < self.ifd_skip_bytes:
                self.ifd_skip_bytes -= len(data)
                return None
            else:
                self.state = 'tiff-ifds'
                self.marker_pos = 0
                return data[self.ifd_skip_bytes:]
        raise RuntimeError('Invalid parsing of the TIFF header')

    def handle_ifd_entry(self, data):
        # Each IFD is 12 bytes. We expect to read 12*self.ifd_count entries
        if self.ifd_count == 0:
            self.state = 'ifd-end'
            return data
        ifd_data, data = self.read_sized_length(data, self.IFD_LEN)
        if not ifd_data:
            return None
        self.ifd_count -= 1
        tag, fmt, components = self.unpack_tiff_data('HHI', ifd_data[0:8])
        total_size = self.COMPONENT_SIZES[fmt] * components
        if total_size > 4 or tag == 0x8769:
            data_offset = self.unpack_tiff_data('I', ifd_data[8:])[0]
            abs_offset = data_offset + self.tiff_start
            self.ifd_offsets[tag] = (abs_offset, total_size, tag, fmt,
                                     self.tiff_alignment)
        else:
            self.tags.append(ExifTag(tag, fmt, ifd_data[8:8+total_size],
                                     self.tiff_alignment))
        return data

    def handle_ifd_end(self, data):
        # We read all entries in the current IFD. Get the next IFD offset
        next_ifd_offset, data = self.read_sized_length(data, 4)
        if not next_ifd_offset:
            return None

        next_ifd_offset = self.unpack_tiff_data('I', next_ifd_offset)[0]

        self.state = 'tag-offsets'
        self.sorted_offsets = self.ifd_offsets.values()
        if next_ifd_offset:
            self.sorted_offsets.append((
                next_ifd_offset + self.tiff_start, -1, -1, -1, -1))
        self.sorted_offsets = filter(lambda x: x[0] >= self.file_offset,
                                     self.sorted_offsets)
        self.sorted_offsets.sort(key=lambda x: x[0])
        return data

    def handle_ifds(self, data):
        ifd_size, data = self.read_sized_length(data, 2)
        if not ifd_size:
            return None
        self.ifd_count = self.unpack_tiff_data('H', ifd_size)[0]
        self.state = 'ifd-entry'
        return data

    def handle_tag_offsets(self, data):
        if self.current_tag is None:
            if not self.sorted_offsets:
                return None
            if self.sorted_offsets[0][0] != self.file_offset:
                # Figure out why the offsets don't work out in some cases
                print 'Warning: Could not find a tag at the offset.'
                return data[1:]
            self.current_tag = self.sorted_offsets[0]
            del self.sorted_offsets[0]
        offset, size, tag, fmt, endian = self.current_tag
        if tag == 0x8769 or tag == -1:
            self.state = 'tiff-ifds'
            self.current_tag = None
            return data

        tag_data, data = self.read_sized_length(data, size)
        if not tag_data:
            return None
        self.tags.append(ExifTag(tag, fmt, tag_data, endian))
        self.current_tag = None
        return data

    def process(self, data):
        if len(data) == 0:
            return

        while data:
            start = len(data)
            if not self.state:
                data = self.check_jpeg_start(data)
            elif self.state == 'exif marker':
                data = self.handle_exif_marker(data)
            elif self.state == 'exif marker data':
                data = self.handle_exif_marker_data(data)
            elif self.state == 'non-exif marker':
                data = self.handle_non_exif_data(data)
            elif self.state == 'tiff-data':
                data = self.handle_tiff_headers(data)
            elif self.state == 'tiff-ifds':
                data = self.handle_ifds(data)
            elif self.state == 'ifd-entry':
                data = self.handle_ifd_entry(data)
            elif self.state == 'ifd-end':
                data = self.handle_ifd_end(data)
            elif self.state == 'tag-offsets':
                data = self.handle_tag_offsets(data)
            else:
                return
            if data:
                self.file_offset += start - len(data)
            else:
                self.file_offset += start
