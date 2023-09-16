'''General API and Base application api'''

import logging

from . import register_api, registers


class BaseAppApi(register_api.RegisterApi):
    '''Common API for all applications'''

    @classmethod
    def __init_subclass__(cls, app_id, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._app_id = app_id

    def start(self, trid):
        '''Start an application'''
        logging.debug(f'Starting app id: {self._app_id} on tracker {trid + 1}')
        self.set_register(registers.GENERAL2_RELOAD, 1, trid)
        self.set_register(registers.GENERAL2_START, int(self._app_id), trid)

    def stop(self, trid):
        '''Stop the currently running application, if applicable'''
        logging.debug(f'Stopping app on tracker {trid + 1}')
        self.set_register(registers.GENERAL2_STOP, 1, trid)
