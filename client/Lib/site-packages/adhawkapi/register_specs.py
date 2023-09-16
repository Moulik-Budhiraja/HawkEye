'''This module defines the embedded Register Specification'''

import abc
import collections
import copy
import dataclasses
import enum
import logging
import math
import struct
import typing

from . import error, normalize, register_spec_defs


class Validators(enum.Enum):
    '''Validator Types'''
    RANGE = 1


class Transformers(enum.Enum):
    '''Enum Types'''
    BITFIELD = 1
    LINEARNORM = 2
    METRIC = 3
    QUANTIZE = 4
    SELECTION = 5


class RegisterSpec:
    '''Hardware register specification'''

    _FORMATS = {'int': 'i', 'uint': 'I', 'float': 'f', 'str': '4s', 'bytes': '4s'}

    def __init__(self, **kwargs):
        # Required Arguments
        self.name = kwargs['name']
        self.bank = kwargs['bank']
        self.register = kwargs['register']

        # Optional Arguments with defaults
        self.default = kwargs.get('default', 0)
        self.version = kwargs.get('version', '0.0.0')
        self.type = kwargs.get('type', 'int')  # refers to the type returned from the hardware
        self.size = kwargs.get('size', 1)  # only if the type is a str
        self.read_access = kwargs.get('read_access', True)
        self.write_access = kwargs.get('write_access', True)
        self.deprecated = kwargs.get('deprecated', False)
        try:
            self.parts = kwargs['parts']
        except KeyError:
            self.parts = [{'name': '', 'offset': 0, 'length': 32, 'validators': {}, 'transformers': {}}]
            # Associate any global validators or transformers with this part
            self.parts[0]['validators'] = kwargs.get('validators', {})
            self.parts[0]['transformers'] = kwargs.get('transformers', {})

        for part in self.parts:
            part['validators'] = self._validator_factory(part.get('validators', {}))
            part['transformers'] = self._transformer_factory(part.get('transformers', {}))

        self._check_spec()

    def _check_spec(self):
        '''Ensure the spec makes sense'''
        try:
            assert self.type in {'int', 'uint', 'float', 'str', 'bytes'}
            if self.size > 1:
                assert self.type in {'str', 'bytes'}, 'If size > 1, type must be str or bytes'
            if len(self.parts) > 1:
                assert self.type == 'uint', 'Multipart registers must have type uint'
        except AssertionError as exc:
            logging.critical(f'Bad definition for {self.name}: {exc}')

    def _handle_input_size(self, value):
        '''Ensure that the input size matches the number of parts this register contains'''
        if len(self.parts) == 1:
            value = [value]
        else:
            try:
                assert isinstance(value, list)
                assert len(value) == len(self.parts)
            except AssertionError:
                raise ValueError(f'{self.name} expects {len(self.parts)} values')
        return value

    def validate(self, value):
        '''Check if the value conforms to the register spec'''
        value = self._handle_input_size(value)
        for idx, part in enumerate(self.parts):
            for validator in part['validators'].values():
                validator.validate(self.name, value[idx])

    def transform(self, value):
        '''Transform the value to the format required by hardware'''
        reg_value = 0
        value = self._handle_input_size(value)
        for idx, part in enumerate(self.parts):
            for transformer in part['transformers'].values():
                value[idx] = transformer.transform(self.name, value[idx])
            if self.type in ['uint']:
                try:
                    reg_value |= value[idx] << part['offset']
                except TypeError:
                    raise ValueError(f'Invalid Type. Expecting {self.type}')
            else:
                # If the type is not int/uint, the register cannot be multipart
                reg_value = value[idx]
        return reg_value

    def invert(self, reg_value):
        '''Transform the value back to the user-facing format'''
        values = [None] * len(self.parts)
        for idx, part in enumerate(self.parts):
            if self.type in ['uint']:
                mask = (1 << (part['offset'] + part['length'])) - 1
                values[idx] = (reg_value & mask) >> part['offset']
            else:
                # If the type is not int/uint, the register cannot be multipart
                values[idx] = reg_value
            for transformer in part['transformers'].values():
                values[idx] = transformer.invert(self.name, values[idx])

        return values[0] if len(self.parts) == 1 else values

    def pack(self, data: typing.Any) -> bytes:
        '''Pack the data of the register based on its type'''
        return struct.pack(self._FORMATS[self.type], data)

    def unpack(self, data: bytes) -> typing.Any:
        '''Unpack the binary data of the register based on its type'''
        return struct.unpack(self._FORMATS[self.type], data)[0]

    @staticmethod
    def _validator_factory(entries):
        '''Factory validators based on the spec'''
        factory_map = {Validators.RANGE.name: ValidateRange}

        collection = collections.OrderedDict()
        for name, properties in entries.items():
            collection[name.upper()] = factory_map[name.upper()](**properties)
        return collection

    @staticmethod
    def _transformer_factory(entries):
        '''Factory transformers based on the spec'''
        factory_map = {
            Transformers.BITFIELD.name: TransformBitfield,
            Transformers.LINEARNORM.name: TransformLinearNorm,
            Transformers.METRIC.name: TransformMetricConversion,
            Transformers.QUANTIZE.name: TransformQuantize,
            Transformers.SELECTION.name: TransformSelection}
        collection = collections.OrderedDict()
        for name, properties in entries.items():
            collection[name.upper()] = factory_map[name.upper()](**properties)
        return collection

    def __repr__(self):
        return self.name


@dataclasses.dataclass
class ValidateRange:
    '''Validate values for numeric properties'''
    min_val: int
    max_val: int

    def validate(self, name, value):
        '''Check if the value falls within the range defined by the spec'''
        if self.min_val > value or self.max_val < value:
            raise ValueError(f'{name} cannot be set to {value}: Valid Range[{self.min_val}, {self.max_val}]')


class TransformBase(abc.ABC):
    '''Abstract base class for transformer classes'''

    @abc.abstractmethod
    def transform(self, name, value):
        '''Transform the value to be written to hardware
           Assumes all validation is already performed
        '''
        pass

    @abc.abstractmethod
    def invert(self, name, value):
        '''Tranform the value read from hardware'''
        pass


class TransformQuantize(TransformBase):

    '''Quantize the value'''

    def __init__(self, **kwargs):
        self.max_val = kwargs.get('max_val')
        self.num_bits = kwargs.get('num_bits')

    def transform(self, name, value):
        '''Quantize the float value'''
        return int((float(value) / self.max_val) * (math.pow(2, self.num_bits) - 1))

    def invert(self, name, value):
        '''Convert the quantized value back to float'''
        return (float(value) / (math.pow(2, self.num_bits) - 1)) * self.max_val


class TransformMetricConversion(TransformBase):
    '''Convert between metric units (ex: Hz to MHz)'''

    def __init__(self, **kwargs):
        self.multiplier = kwargs.get('multiplier')

    def transform(self, name, value):
        '''Convert a value to the metric unit used by hardware
        :param name: (str) The name of the register spec
        :param value: (int or float) The value in units being displayed to the user
        :return: (int) The value in units used by the hardware
        '''
        return int(value * self.multiplier)

    def invert(self, name, value):
        '''Convert the value back to units displayed to the user'''
        return float(value) / self.multiplier


class TransformBitfield(TransformBase):
    '''Transform a list of choices to a bitfield and back'''

    def __init__(self, **kwargs):
        self.choices = kwargs.get('choices')

    def transform(self, name, value):
        '''Transform a list of choices to a bitfield
        :param name: (str) The name of the register spec
        :param value: (set[int]) The list of bits to enable. Example: [0, 11]
        :raises ValueError: If the choice isn't a valid option for the register
        :return: (int) A bitfield representing the enabled choices
        '''
        bitfield = 0
        for choice in value:
            bitfield |= 1 << self._choice_to_bit(name, choice)
        return bitfield

    def _choice_to_bit(self, name, choice):
        try:
            _ = self.choices[choice]
        except KeyError:
            raise ValueError(f'{name} cannot be set to {choice}. Valid Options: {self.choices}')
        return choice

    def invert(self, name, value):
        '''Converts the bitfield back to a list of choices
        :param name: (str) The name of the register spec
        :param value: (int) An int representing a bitfield
        :return: ({int: description}) Dict of enabled choices
        '''
        choices = {}
        for bit, description in self.choices.items():
            if value & (1 << bit):
                choices[bit] = description
        return list(choices.keys())


@dataclasses.dataclass
class TransformSelection(TransformBase):
    '''Transform a selection to a number and back.
    Use this instead of a TransformBitfield when you only want a single option to be enabled
    '''

    def __init__(self, **kwargs):
        self.choices = kwargs.get('choices')

    def transform(self, name, value):
        '''Transform a selection to an integer
        :param name: (str) The name of the register spec
        :param value: (int) The number to enable. Example: 0
        :raises ValueError: If the choice isn't a valid option for the register
        :return: (int) A value representing the choice
        '''
        try:
            _ = self.choices[value]
        except KeyError:
            raise ValueError(f'{name} cannot be set to {value}. '
                             f'Valid Options: {self.choices}')
        return value

    def invert(self, name, value):
        '''Converts the bitfield back to a list of choices
        :param name: (str) The name of the register spec
        :param value: (int) An int representing the selection
        :return: ({int: description}) A pair representing the enabled choice
        '''
        try:
            _ = self.choices[value]
        except KeyError:
            logging.warning(
                f'Read unexpected value {value} for {name}. '
                f'Supported options: {self.choices}')
        return value


@dataclasses.dataclass
class TransformLinearNorm(TransformBase):
    '''Perform linear normalization'''

    def __init__(self, **kwargs):
        self.userrange_min = kwargs.get('userrange_min', 0)
        self.userrange_max = kwargs.get('userrange_max', 1023)
        self.hwrange_min = kwargs.get('hwrange_min', 0)
        self.hwrange_max = kwargs.get('hwrange_max', 4095)

    userrange: tuple = (0, 1023)
    hwrange: tuple = (0, 4095)

    def transform(self, name, value):
        '''Perform linear normalization from the input range to the output range'''
        userrange = (self.userrange_min, self.userrange_max)
        hwrange = (self.hwrange_min, self.hwrange_max)
        try:
            return int(normalize.linearnorm(value, userrange, hwrange))
        except TypeError as exc:
            raise ValueError(f'{name} cannot be set to {value}.\n{exc}')

    def invert(self, name, value):
        '''Perform linear normalization from the input range to the output range'''
        userrange = (self.userrange_min, self.userrange_max)
        hwrange = (self.hwrange_min, self.hwrange_max)
        try:
            return normalize.linearnorm(value, hwrange, userrange)
        except TypeError as exc:
            raise ValueError(f'{name} cannot be set to {value}.\n{exc}')


def load_reg_spec(spec_defs=None):
    '''Read and load the register specification
    :return dictionary in the following form
    {
        bank_key:
            bank: <>
            name: <>
            registers:
            {
                register_key : RegisterSpec
                register_key : RegisterSpec
            }
        ...
    }
    '''
    spec_defs = register_spec_defs.SPEC_DEFS if spec_defs is None else spec_defs
    transformed_specs = copy.deepcopy(spec_defs)
    for bank_spec in transformed_specs.values():
        for reg_key, reg_spec in bank_spec['registers'].items():
            reg_spec.update({'bank': bank_spec['bank'],
                             'name': f'{bank_spec["name"]} {reg_spec["name"]}'})
            bank_spec['registers'][reg_key] = RegisterSpec(**reg_spec)

    return collections.OrderedDict(sorted(transformed_specs.items(),
                                          key=lambda kv: kv[1]['bank']))


def get_reg_spec(reg_specs, bank_key, reg_key):
    '''Get the register spec given a bank and register key'''
    try:
        return reg_specs[bank_key]['registers'][reg_key]
    except KeyError:
        raise error.InternalError(f'({bank_key},{reg_key}) is not defined in the register specification')
