# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a video streaming server
# Copyright (C) 2004 Fluendo
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sys

_do_logging = False

def log(m):
    global _do_logging
    if _do_logging:
        sys.stderr.write(m)
        sys.stderr.flush()
    
def msg(category, *args):
    log('[%s] %s\n' % (category, ' '.join(args)))

def warning(category, *args):
    log('[%s] WARNING: %s\n' % (category, ' '.join(args)))

def error(category, *args):
    log('[%s] ERROR: %s\n' % (category, ' '.join(args)))
    raise SystemExit

def enableLogging():
    global _do_logging
    _do_logging = True

def disableLogging():
    global _do_logging
    _do_logging = False
    
