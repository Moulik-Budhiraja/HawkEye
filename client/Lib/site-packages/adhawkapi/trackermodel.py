r"""Model used to store run-time configuration data specifically for the trackers.

Example Usage:
==============

import adhawkapi
import adhawkapi.trackermodel
import adhawktools.model

# Set up communication
api = adhawkapi.register_api.RegisterApi('COM15')

# Initialize a model
cfg = adhawkapi.trackermodel.TrackerModel()

# Initialize the model <-> hardware interface
# updating the model will automatically update the hardware
hw = adhawkapi.config_reg_map.HardwareSubsystem(cfg)

# Load the model with values from hardware
cfg.load(adhawktools.model.Subsystem.HARDWARE, check_errors=False)

# Read values
cfg.get_value(adhawkapi.trackermodel.construct_path(0, adhawkapi.configs.PD_ENABLE, pd_id=0))

# Update the model with values from a config file
cfg.load_configs_from_file('configs\EVK3.4-12.json')

# Update individual configs
cfg.update(
    adhawktools.model.Subsystem.USER_INTERFACE,
    { adhawkapi.trackermodel.construct_path(1, adhawkapi.configs.PD_ENABLE, pd_id=0): False,
        adhawkapi.trackermodel.construct_path(0, adhawkapi.configs.TRACKER_XMEAN_PCT): 50})

# Flush the settings in hardware (TODO: TRSW-1608: implement api.reload())
api.set_register(adhawkapi.registers.GENERAL2_FLUSH, 1)
api.shutdown()
"""

import re
import adhawktools.model


_MODEL_FILENAME = 'adhawkapi/configmodel_defs/toplevel.yaml'
_MODEL_OUT_FILENAME = 'adhawkapi/configmodel.py'
_RE_PATH = re.compile(
    r'(tracker(?P<tracker_id>\d)\/)?((?P<pd_type>(detector|pupilpd|pd))(?P<pd_id>\d)\/)?(?P<subpath>\S+)')


class TrackerModel(adhawktools.model.Model):
    '''Specialization of the model to handle per tracker and per pd more conveniently'''

    def __init__(self):
        from . import configmodel
        super().__init__(configmodel.MODEL)


def construct_path(tracker_id, path='', **extra_args):
    '''Build a config path'''
    tracker_id = f'tracker{tracker_id}/' if tracker_id is not None else ''
    pd_type = extra_args.get('pd_type', 'pd')
    pd_id = f'{pd_type}{extra_args["pd_id"]}/' if 'pd_id' in extra_args else ''
    return f'{tracker_id}{pd_id}{path}'


def parse_path(path):
    '''Extract tracker, pd and config path from the specified path'''
    match = re.match(_RE_PATH, path)
    tracker_id = int(match.group('tracker_id')) if match.group('tracker_id') else None
    extra_args = {}
    if match.group('pd_type'):
        pd_type = match.group('pd_type')
        pd_id = int(match.group('pd_id'))
        extra_args.update({'subgroup': pd_type, 'pd_type': pd_type, 'pd_id': pd_id})
    return tracker_id, match.group('subpath'), extra_args


def _print_heading(outfile):
    import sys
    heading = '''\
\'''This module provides the list of known configurations that can be used
throughout the application.

Automatically generated using the following:
python -c "import adhawkapi.trackermodel; adhawkapi.trackermodel.main()" {}

''\'
'''
    print(heading.format(' '.join(sys.argv[1:])), file=outfile)


def _print_paths(trackermodel_def, outfile):
    '''Generates a list of path variables for current model'''

    pd_prefixes = ('pd', 'pupilpd', 'detector')
    trackermodel = adhawktools.model.Model(trackermodel_def)
    all_nodes = [path.split('/') for path in trackermodel.all_nodes]
    nontracker_nodes = [item for item in all_nodes if not item[0].startswith('tracker')]
    tracker_nodes = [item for item in all_nodes if item[0] == 'tracker0']
    tracker_nodes_filtered = [item[1:] for item in tracker_nodes
                              if len(item) > 1 and
                              not item[1].startswith(pd_prefixes) and
                              item[1] != 'autotune']

    pd_prefixes_0 = [f'{prefix}0' for prefix in pd_prefixes]
    pd_nodes = [item[2:] for item in tracker_nodes if len(item) > 2 and item[1].startswith(tuple(pd_prefixes_0))]
    autotune_nodes = [item[1:] for item in tracker_nodes
                      if len(item) > 1 and item[1] == 'autotune']
    nontracker_paths = [(item, item) for item in nontracker_nodes]
    tracker_paths = [(('tracker', *item), item) for item in tracker_nodes_filtered]
    pd_paths = [(('pd', *item), item) for item in pd_nodes]
    autotune_paths = [(item, item) for item in autotune_nodes]
    for nameelems, pathelems in nontracker_paths + tracker_paths + pd_paths + autotune_paths:
        name = '_'.join(nameelems)
        path = '/'.join(pathelems)
        print(f'{name.upper()} = \'{path}\'', file=outfile)


def main():
    '''Standalone generator for the configs constants'''
    import argparse
    import os
    import pathlib
    import black
    from adhawktools import multifileyaml
    parser = argparse.ArgumentParser(description='Configuration path generator')
    parser.add_argument('-o', '--output', required=True, help='Output path')
    args = parser.parse_args()
    with open(_MODEL_FILENAME) as infile:
        trackermodel_def = multifileyaml.load(infile)
    with open(os.path.join(args.output, 'configs.py'), 'w') as outfile:
        _print_heading(outfile)
        _print_paths(trackermodel_def, outfile)
    generated_model_file = pathlib.Path(args.output) / 'configmodel.py'
    with open(generated_model_file, 'w') as outfile:
        _print_heading(outfile)
        print('# pylint: disable=too-many-lines', file=outfile)
        print(f'MODEL = {repr(trackermodel_def)}', file=outfile)
    # Format the file
    black.format_file_in_place(
        generated_model_file, fast=False, mode=black.FileMode(string_normalization=False),
        write_back=black.WriteBack.YES)
