import socket
import time
import types
import sys
import yaml
import copy
import logging
from logging import info, warning, critical, debug
import asyncio



class BLError(Exception):
    """This is the base class for a broader range of errors coming from the MDrive motors"""
    def __init__(self, expression=None, message=None, fatalError=True, canRestart=True):
        self.expression = expression
        self.message = message
        full_message = "{}: {}".format(expression, message)
        warning(full_message)
        print(full_message)

class BLCommandError(BLError):
    pass


class SPECCommandError(BLCommandError):
    pass





class BLConfigFileError(BLError):
    pass


class SPECError(BLError):
    pass



class BLCommandError(BLError):
    pass

class SPECCommunicationError(BLCommandError):
    pass


class SISControlError(BLError):
    pass
