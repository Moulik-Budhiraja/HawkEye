'''This module is used to register different AdHawk API Packets'''

import abc
import collections
import dataclasses
import enum
import logging
import struct
import typing


class Wildcard(enum.Enum):
    '''Wildcard prefix match'''
    WILDCARD = '*'


class Trie:
    '''Minimal Trie used to register the header of different packet types
    This allows us to quickly indentify the packet type of a packet by searching for the longest prefix match
    Usage:
        t = Trie()
        t.add((0xa3, 0x2, 0x4), classname)
        c = t.get((0xa3, 0x2, 0x4, 0x0, 0x2))
        assert c == classname
    '''

    def __init__(self):
        self._root = {}

    def add(self, prefix: collections.abc.Iterable, value: typing.Any):
        '''Add a new prefix to the trie
        prefix (iterable): (0xa3, 0x2, 0x4)
        value (any): The value mapped to the prefix
        '''
        node = self._root
        for idx, element in enumerate(prefix, 1):
            node = node.setdefault(element, value if idx == len(prefix) else {})

    def get(self, prefix: collections.abc.Iterable) -> typing.Any:
        '''Iterates over the prefix in the trie, finds the longest match and returns the value
        Args:
            prefix (iterable): The prefix to look for in the trie (ex: (0xa3, 0x2, 0x4))
        Returns:
            The value associated with the prefix
        Raises:
            KeyError: If the prefix isn't found
        '''
        node = self._root
        for element in prefix:
            try:
                node = node[element]
            except KeyError:
                try:
                    # Check if a wildcard was registered
                    node = node[Wildcard.WILDCARD.value]
                except KeyError:
                    raise KeyError(prefix)
            if not isinstance(node, dict):
                return node
        raise KeyError(prefix)


class ApiPacket(abc.ABC):
    '''Base class for different AdHawk API packets
    Inheriting from this class automatically registers the header format for this packet type
    Usage:
        @dataclasses.dataclass
        TestPacket(ApiPacket, header=(0xa3, 0x2, 0x4)):
            field1: int
            field2: float
            field3: bytes

            def payload_format(cls):
                return '<Bf4s'

        pkt = ApiPacket.from_pkt(b'\xa3\x02\x04\x01\x00\x00\xc0?test)
        print(pkt.data)
        >>> {field1: 1, field2: 1.5, field3: b'test'}
    '''
    _MAX_PREFIX_LENGTH = 6

    _subclasses = Trie()
    _header = None
    _debug = False

    @classmethod
    def __init_subclass__(cls, header: collections.abc.Iterable[enum.Enum]):
        super().__init_subclass__()
        prefix = tuple(t.value for t in header)
        cls._header = header
        cls._header_format = f'<{len(cls._header)}B'
        cls._header_len = struct.calcsize(cls._header_format)
        cls._subclasses.add(prefix, cls)

    @classmethod
    @abc.abstractmethod
    def payload_format(cls) -> str:
        '''Return the struct format for the payload (ex: '<Bf4s')
        If the packet is of a variable length, the child class MUST implement the @pack() and @unpack() functions
        '''
        raise NotImplementedError

    @classmethod
    def from_pkt(cls, pkt: bytes) -> tuple[typing.Any, int]:
        '''Create an instance of the class given a packet
        Args:
            pkt (bytes): The packet including the header and payload
        Returns:
            ApiPacket: An instance of the resolved ApiPacket type
            int: The length of the packet buffer that was unpacked (length of header + length of payload)
        '''
        # Use at most the first <_MAX_PREFIX_LENGTH> bytes of the packet to figure out the packet type
        prefix = struct.unpack_from(f'<{min(ApiPacket._MAX_PREFIX_LENGTH, len(pkt))}B', pkt)
        try:
            _subclass = cls._subclasses.get(prefix)
        except KeyError:
            raise ValueError(f'No registered packet with prefix {list(map(hex, prefix))}')

        try:
            # Unpack the bytes provided and create the instance of the subclass
            pkt_len, data = _subclass.unpack(pkt)
            instance = _subclass(*data)
        except (struct.error, TypeError) as exc:
            raise TypeError(f'Unable to unpack {_subclass}') from exc

        if cls._debug:
            logging.debug(instance.info())
            logging.debug(f'{pkt_len} bytes: {bytes(pkt[:pkt_len])}')
            logging.debug(instance.data())
        return instance, pkt_len

    @classmethod
    def info(cls) -> str:
        '''Returns information about the packet'''
        return f'header: {cls._header}, format: {cls._header_format} + {cls.payload_format()}'

    @classmethod
    def unpack(cls, pkt: bytes) -> tuple[int, typing.Any]:
        '''Unpacks the packet using the header and payload format
        MUST be overridden by child classes that have variable packet sizes

        Args:
            pkt (bytes): The packet including the header and payload
        Returns:
            int: The length of the packet buffer that was unpacked (length of header + length of payload)
            iterable: The data unpacked from the packet
        '''
        pkt_len = cls._header_len + struct.calcsize(cls.payload_format())
        data = struct.unpack_from(cls.payload_format(), pkt, cls._header_len)
        return pkt_len, data

    def pack(self) -> bytes:
        '''Packs the data into a packet using the header and payload format
        Returns:
            bytes: The packet in bytes
        '''
        header = struct.pack(self._header_format, *self._header)

        # Only pack fields that were part of the initialization (unpack)
        fields = tuple(getattr(self, field.name) for field in dataclasses.fields(self) if field.init)
        data = struct.pack(self.payload_format(), *fields)
        return header + data

    def data(self) -> dict:
        '''Returns the data in the packet as a dictionary'''
        # dataclass.asdict() performs recursive deepcopies, use the following to create a shallow copy
        return dict((field.name, getattr(self, field.name)) for field in dataclasses.fields(self))
