"""This module defines the interface between the model and the hardware registers
"""

import logging

from adhawktools import model

from . import blob_api, configmap, error, register_api, trackermodel
from .base import MinimumAPIVersion


class HardwareSubsystem:
    '''Interface between the model and the hardware'''

    def __init__(self, configmodel):
        self._model = configmodel
        self._model.add_callback(model.Subsystem.HARDWARE, self._update_hardware, '**')
        self._model.add_loader(model.Subsystem.HARDWARE, self._load_model)

    @staticmethod
    def _get_api(source: configmap.DataSource):
        '''Given the config path, construct the API'''
        if source == configmap.DataSource.REGISTERS:
            return register_api.RegisterApi()
        return blob_api

    def _load_model(self, path):
        '''Update the model once the register api is available'''

        tracker_id, config, extra_args = trackermodel.parse_path(path)
        config_key = (config, extra_args['subgroup']) if extra_args.get('subgroup') else config
        handler = configmap.get_handler(config_key)

        api = self._get_api(handler.source)
        if api is None:
            return

        try:
            value = handler.read(api, self._model, tracker_id, config, **extra_args)
        except MinimumAPIVersion as exc:
            logging.warning(f'Failed to read {path}: {exc}')
        except ValueError as exc:
            raise ValueError(f'Failed to read {path}: {exc}')
        except error.Error as exc:
            logging.error(f'Failed to read {path}: {exc}')
            raise
        else:
            self._model.update(model.Subsystem.HARDWARE, {path: value})

    def _update_hardware(self, path, value, _reason):
        '''Callback executed when there have been updates to the model
        '''
        tracker_id, config, extra_args = trackermodel.parse_path(path)
        config_key = (config, extra_args['subgroup']) if extra_args.get('subgroup') else config
        handler = configmap.get_handler(config_key)

        api = self._get_api(handler.source)
        if api is None:
            return

        # cache the current model value (in case reading the device value into cache fails)
        cache_value = self._model.get_value(path)

        try:
            # cache the current value from the hardware
            cache_value = handler.read(api, self._model, tracker_id, config, **extra_args)
            handler.write(value, api, self._model, tracker_id, config, **extra_args)

            # update any related configs
            related_configs = self._model.get(path).get('related', [])
            for related_config in related_configs:
                related_path = trackermodel.construct_path(tracker_id, related_config, extra_args=extra_args)
                related_handler = configmap.get_handler(related_config)
                related_value = related_handler.read(api, self._model, tracker_id, related_config, **extra_args)
                self._model.update(model.Subsystem.HARDWARE, {related_path: related_value})

        except MinimumAPIVersion as exc:
            # if we fail to apply the change, update the model with the cache value
            # and provide the reason
            self._model.update(model.Subsystem.HARDWARE, {path: cache_value}, str(exc))
        except (ValueError, error.Error) as exc:
            logging.error(f'Failed to set {path} to {value}: {exc}')
            if cache_value is not None:
                self._model.update(model.Subsystem.HARDWARE, {path: cache_value}, str(exc))
