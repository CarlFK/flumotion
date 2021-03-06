# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.

"""
Utility functions for Nagios.
"""

import sys

from twisted.internet import reactor

from flumotion.common import common, log
from flumotion.extern.command import command

__version__ = "$Rev$"


class LogCommand(command.Command, log.Loggable):

    def __init__(self, parentCommand=None, **kwargs):
        command.Command.__init__(self, parentCommand, **kwargs)
        self.logCategory = self.name

    # command.Command has a fake debug method, so choose the right one

    def debug(self, format, *args):
        kwargs = {}
        log.Loggable.doLog(self, log.DEBUG, -2, format, *args, **kwargs)


def findComponent(planet, avatarId):
    """
    Finds the component with the given avatarId in the given planet.

    returns: the component state or None.
    """
    flowName, componentName = common.parseComponentId(avatarId)

    if flowName == 'atmosphere':
        for c in planet.get('atmosphere').get('components'):
            if c.get('name') == componentName:
                return c
        return None

    for f in planet.get('flows'):
        if f.get('name') == flowName:
            for c in f.get('components'):
                if c.get('name') == componentName:
                    return c
    return None

# Nagios has standard exit codes
# We cheat by putting the exit code in the reactor.


def ok(msg):
    sys.stdout.write('OK: %s\n' % msg)
    reactor.exitStatus = 0
    return 0


def warning(msg):
    sys.stdout.write('WARNING: %s\n' % msg)
    reactor.exitStatus = 1
    return 1


def critical(msg):
    sys.stdout.write('CRITICAL: %s\n' % msg)
    reactor.exitStatus = 2
    return 2


def unknown(msg):
    sys.stdout.write('UNKNOWN: %s\n' % msg)
    reactor.exitStatus = 3
    return 3

# equivalent exceptions that allow us to stop deferred flows


class NagiosException(Exception):
    message = None
    exitStatus = None

    def __init__(self, message, exitStatus):
        self.message = message
        self.exitStatus = exitStatus
        self.args = (message, exitStatus)


class NagiosWarning(NagiosException):

    def __init__(self, message):
        NagiosException.__init__(self, 'WARNING: %s' % message, 1)


class NagiosCritical(NagiosException):

    def __init__(self, message):
        NagiosException.__init__(self, 'CRITICAL: %s' % message, 2)


class NagiosUnknown(NagiosException):

    def __init__(self, message):
        NagiosException.__init__(self, 'UNKNOWN: %s' % message, 3)
