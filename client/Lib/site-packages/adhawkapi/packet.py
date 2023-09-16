'''This module contains the packet abstraction used by AdHawk's communication framework'''

import ctypes
import enum
import struct

from . import defaults, error, utils


class UnsupportedPacket(error.Error):
    '''Exception class for unsupported packet types'''
    pass


class PacketType(enum.IntEnum):
    '''List of AdHawk's packet types'''
    READ = 0
    WRITE = 1
    STREAM = 2
    ERROR = 3
    HIGH_PRIORITY_STREAM = 5
    ISP_WRITE = 10
    ISP_READ = 11


class Packet:
    """
    AdHawk serial packet structure obeys the following format:

    `[Metadata] [Header] [Payload]`

    There are two ways of constructing packets:
    1. The `__init__` method accepts raw byte array data, and constructs the packet, useful when
       reading a packet from a byte stream.
    2. The `construct` accepts packet data parameters, and
       constructs the byte array, useful for writing a packet to a byte stream.
    """

    def __init__(self, packet_data, metadata, header_offset):
        self._packet_data = packet_data
        self._metadata = metadata
        self._header_offset = header_offset
        self._header_len = metadata.header_len

    @property
    def packet_data(self):
        '''Returns the full packet buffer containing metadata, header, and payload'''
        return self._packet_data

    @property
    def metadata(self):
        """ get the metadata field """
        return self._metadata

    @property
    def header(self):
        """ get the header byte """
        return self._packet_data[self._header_offset:self._header_offset + self._header_len]

    @property
    def payload(self):
        """ get the payload bytes """
        return self._packet_data[self._header_offset + self._header_len:]

    def unpack_payload(self, fmt):
        """ get the payload bytes """
        return utils.unpack_stream(fmt, self._packet_data, self._header_offset + self._header_len)

    def unpack_iter_payload(self, fmt_const, fmt_iter):
        """ get the payload bytes """
        return utils.unpack_iter_stream(fmt_const, fmt_iter, self._packet_data,
                                        self._header_offset + self._header_len)


class PacketMetadataV1:
    '''Version 1 of packet metadata with combined routing/control'''

    class Metadata(ctypes.Union):
        """ Metadata byte structure """
        class MetadataFields(ctypes.LittleEndianStructure):
            """ Definition for bitfields in the metadata byte """
            _fields_ = [
                ("dev_id", ctypes.c_uint8, 1),
                ("extended", ctypes.c_uint8, 1),
                ("length", ctypes.c_uint8, 4),
                ("stream", ctypes.c_uint8, 1),
                ("error", ctypes.c_uint8, 1)
            ]
        _pack_ = 1
        _fields_ = [("fields", MetadataFields), ("byte", ctypes.c_uint8)]

    def __init__(self, packet_data):
        self._data = self.Metadata()
        self._data.byte = packet_data[0]

    @property
    def header_len(self):
        '''Returns the length of the header'''
        return 1 if self.stream else 2

    @property
    def dst_id(self):
        '''Returns the device id that this packet is destined for'''
        return self._data.fields.dev_id + self._data.fields.extended * 2

    @property
    def src_id(self):
        '''Returns the device id that generated this packet'''
        # we can't distinguish between source and destination in this version
        return self.dst_id

    @property
    def stream(self):
        '''Returns whether this packet is a stream packet'''
        return self._data.fields.stream

    @property
    def error(self):
        '''Returns whether this packet is a response error packet'''
        return self._data.fields.error

    @property
    def high_priority(self):
        '''Returns whether this packet is high priority packet'''
        return self._data.fields.stream == 0


class PacketV1Factory:
    '''Factory for Version 1 of packet metadata'''

    metadata_length = 1
    '''start of the header (or length of metadata)'''

    @staticmethod
    def validate(pkt):
        '''Check that the requested packet is valid and supported'''
        if not isinstance(pkt.metadata, PacketMetadataV1):
            raise UnsupportedPacket('Invalid packet metadata')

    @classmethod
    def construct_from_raw(cls, packet_data):
        '''build and return an instance of this class'''
        return Packet(packet_data, PacketMetadataV1(packet_data), cls.metadata_length)

    @classmethod
    def construct(cls, pkttype, dev_id, payload):
        '''build and return an instance of this class'''
        extended = 0
        if dev_id in (defaults.CONTROL_DEV_ID, 2):
            extended = 1
            dev_id = 0
        elif dev_id > 2:
            raise UnsupportedPacket('Device id greater than 2 is not supported')

        assert len(payload) < 0xf
        metadata = PacketMetadataV1.Metadata()
        # pylint: disable=attribute-defined-outside-init
        metadata.byte = 0
        metadata.fields.dev_id = dev_id
        metadata.fields.extended = extended
        metadata.fields.stream = (1 if pkttype == PacketType.STREAM else 0)
        metadata.fields.length = len(payload)
        packet_data = bytes([metadata.byte]) + payload
        return Packet(packet_data, PacketMetadataV1(packet_data), cls.metadata_length)


class PacketMetadataV2:
    '''Version 2 of packet metadata with separated routing and control'''

    class Metadata(ctypes.Union):
        """ Metadata byte structure """
        class MetadataFields(ctypes.LittleEndianStructure):
            """ Definition for bitfields in the metadata byte """
            _fields_ = [
                ("src_id", ctypes.c_uint8, 4),
                ("dst_id", ctypes.c_uint8, 4),
                ("pkttype", ctypes.c_uint8, 7),
                ("ext", ctypes.c_uint8, 1),
            ]
        _fields_ = [("fields", MetadataFields), ("bytes", ctypes.c_uint16)]

    def __init__(self, packet_data, pkt_offset=0):
        self._data = self.Metadata()
        self._data.bytes = struct.unpack_from('<H', packet_data, pkt_offset)[0]

    @property
    def header_len(self):
        '''Returns the length of the header'''
        return 1 if self.stream else 2

    @property
    def dst_id(self):
        '''Returns the device id that this packet is destined for'''
        # we can't distinguish between source and destination in this version
        return self._data.fields.dst_id

    @property
    def src_id(self):
        '''Returns the device id that generated this packet'''
        # we can't distinguish between source and destination in this version
        return self._data.fields.src_id

    @property
    def stream(self):
        '''Returns whether this packet is a stream packet'''
        return self._data.fields.pkttype in {PacketType.STREAM, PacketType.HIGH_PRIORITY_STREAM}

    @property
    def error(self):
        '''Returns whether this packet is a response error packet'''
        return self._data.fields.pkttype == PacketType.ERROR

    @property
    def high_priority(self):
        '''Returns whether this packet is high priority packet'''
        return self._data.fields.pkttype != PacketType.STREAM

    @property
    def write(self):
        '''Returns whether the packet performs a write'''
        return self._data.fields.pkttype in [PacketType.WRITE, PacketType.ISP_WRITE]


class PacketV2Factory:
    '''Factory for Version 2 of packet metadata'''

    metadata_length = 2
    '''start of the header (or length of metadata)'''

    _pkt_prefix = b''
    '''used for supporting v2inv3'''

    @staticmethod
    def validate(pkt):
        '''Check that the requested packet is valid and supported'''
        if not isinstance(pkt.metadata, PacketMetadataV2):
            raise UnsupportedPacket('Invalid packet metadata')

    @classmethod
    def construct_from_raw(cls, packet_data):
        '''build and return an instance of this class'''
        packet_metadata = PacketMetadataV2(packet_data, len(cls._pkt_prefix))
        return Packet(packet_data, packet_metadata, cls.metadata_length)

    @classmethod
    def construct(cls, pkttype, dev_id, payload):
        """ build and return an instance of this class """
        metadata = PacketMetadataV2.Metadata()
        # pylint: disable=attribute-defined-outside-init
        metadata.byte = 0
        metadata.fields.pkttype = pkttype
        metadata.fields.src_id = defaults.HOST_DEV_ID
        metadata.fields.dst_id = dev_id
        if pkttype in (PacketType.READ, PacketType.ISP_READ):
            assert len(payload) == 2
            # add dummy payload
            payload = payload + struct.pack('<I', 0)
        packet_data = cls._pkt_prefix + struct.pack('<H', metadata.bytes) + payload
        packet_metadata = PacketMetadataV2(packet_data, len(cls._pkt_prefix))
        return Packet(packet_data, packet_metadata, cls.metadata_length)


class PacketV2inV3Factory(PacketV2Factory):
    '''Factory for Version 2 of packet metadata encapsulated with 0xa0'''

    metadata_length = PacketV2Factory.metadata_length + 1  # 0xa0 encapsulation
    _pkt_prefix = b'\xa0'


class PublicPacketMetadata:
    ''' Public packet type'''

    def __init__(self, packet_data):
        self._is_stream = (packet_data[0] & 0xa0 != 0x80) and packet_data[0] != 0xa1 and packet_data[0] != 0xae
        self._is_high_priority = not self._is_stream or packet_data[0] == 0xa3 or packet_data[0] == 0x02

    @property
    def header_len(self):
        '''Returns the length of the header'''
        return 1

    @property
    def stream(self):
        '''Returns whether this packet is a stream packet'''
        return self._is_stream

    @property
    def error(self):
        '''Returns whether this packet is a response error packet'''
        return False

    @property
    def src_id(self):
        '''Just a stub because this is not a thing in the packet class'''
        return 0

    @property
    def high_priority(self):
        '''Returns whether this packet is high priority packet'''
        return self._is_high_priority


class PublicPacketFactory:
    ''' Public packet type'''

    metadata_length = 1
    '''The public packet doesn't actually have metadata. It only has a header.
    Since this is used to determine how to much to decode to understand the packet,
    it is set to the length of the header.
    '''

    @classmethod
    def construct_from_raw(cls, packet_data):
        '''build and return an instance of this class'''
        return Packet(packet_data, PublicPacketMetadata(packet_data), 0)

    @classmethod
    def construct(cls, pkttype, payload):
        '''Build and return an instance of this class'''
        packet_data = struct.pack('<B', pkttype)
        if payload:
            packet_data += payload

        return Packet(packet_data, PublicPacketMetadata(packet_data), 0)


class PacketV3Factory:
    '''Factory class for Version 3 of packet metadata'''

    # used to determine how much to decode to understand the packet
    metadata_length = max(PublicPacketFactory.metadata_length, PacketV2inV3Factory.metadata_length)

    @staticmethod
    def validate(pkt):
        '''Check that the requested packet is valid and supported'''
        if not isinstance(pkt.metadata, PacketMetadataV2) \
                and not isinstance(pkt.metadata, PublicPacketMetadata):
            raise UnsupportedPacket('Invalid packet metadata')

    @staticmethod
    def construct_from_raw(packet_data):
        '''Creates either a V2inV3 or Public metadata based on input data'''
        prefix = packet_data[0]
        if prefix == 0xa0:
            return PacketV2inV3Factory.construct_from_raw(packet_data)
        return PublicPacketFactory.construct_from_raw(packet_data)

    @staticmethod
    def construct(*args, **kwargs):
        '''Creates a proprietary adhawk packet'''
        return PacketV2inV3Factory.construct(*args, **kwargs)
