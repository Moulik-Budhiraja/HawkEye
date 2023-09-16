'''This module defines the API to access the hardware registers'''
import collections
import logging

from . import register_specs
from .base import BaseApi, MinimumAPIVersion
from .capi.py import libregisterapi
from .version import SemanticVersion


class RegisterApi(BaseApi):
    '''Hardware Register API'''

    _reg_specs = collections.OrderedDict()
    '''Internal data structure that holds the register specification'''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self._reg_specs:
            self._load_reg_spec()

    def dump(self, trid=None):
        '''Dump all the registers and return it as a generator'''
        for bank_key, bank in self._reg_specs.items():
            for reg_key, reg_spec in bank['registers'].items():
                if not reg_spec.read_access:
                    continue
                try:
                    value = self.get_register((bank_key, reg_key), trid)
                except MinimumAPIVersion as exc:
                    logging.warning(exc)
                    continue
                yield f'{(bank_key, reg_key)}: {value}'

    def set_register(self, name, value, trid=None):
        '''Set the value of a register
        Args:
            name: constant from registers.py
            value: the value to set
            trid: (int) target tracker id if applicable, or None for system requests
        Returns:
            Response from the device
        Raises:
            ValueError if the value is not valid
            MinimumAPIVersion if this register is not supported by the firmware
        '''
        reg_spec = register_specs.get_reg_spec(self._reg_specs, *name)
        self._check_compatibility(reg_spec)
        reg_value = reg_spec.transform(value)
        if reg_spec.type in ('str', 'bytes'):
            paddedval = f'{value:\0<{reg_spec.size * 4}}'
            for offset in range(reg_spec.size):
                libregisterapi.write(reg_spec.bank, reg_spec.register + offset,
                                     paddedval[offset * 4:offset * 4 + 4].encode(), trid)
        else:
            # logging.debug(f'{name}: user value {value}, reg value {reg_value}')
            valbuf = reg_spec.pack(reg_value)
            libregisterapi.write(reg_spec.bank, reg_spec.register, valbuf, trid)

    def get_register(self, name, trid=None):
        '''Get the value of a register
        Args:
            name: constant from registers.py
            trid: (int) target tracker id if applicable, or None for system requests
        Returns:
            The value of the register
        Raises:
            MinimumAPIVersion if this register is not supported by the firmware
        '''
        reg_spec = register_specs.get_reg_spec(self._reg_specs, *name)
        self._check_compatibility(reg_spec)
        if reg_spec.type in ('str', 'bytes'):
            reg_value = b''
            for offset in range(reg_spec.size):
                reg_value += libregisterapi.read(reg_spec.bank, reg_spec.register + offset, trid)
            if reg_spec.type == 'str':
                reg_value = reg_value.decode(errors='ignore').rstrip('\0')
        else:
            response = libregisterapi.read(reg_spec.bank, reg_spec.register, trid)
            reg_value = reg_spec.unpack(response)
        # print(f'{name}: reg value {reg_value}')
        value = reg_spec.invert(reg_value)
        if isinstance(value, float):
            value = round(value, 2)
        # print(f'{name}: user value {value}')
        return value

    def _check_compatibility(self, reg_spec):
        major, minor, patch = reg_spec.version.split('.')
        reg_version = SemanticVersion(major, minor, patch)
        if SemanticVersion.compare(self.firmware_info.api_version, reg_version) < 0:
            raise MinimumAPIVersion(f'{reg_spec.name} is not supported in firmware {self.firmware_info.api_version}')

    @classmethod
    def _load_reg_spec(cls):
        '''Read and load the register specification
        '''
        if cls._reg_specs:
            # Previously loaded by another instance
            return
        cls._reg_specs = register_specs.load_reg_spec()
