# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# flumotion/worker/main.py: main function of flumotion-worker
#
# Flumotion - a streaming media server
# Copyright (C) 2004 Fluendo, S.L. (www.fluendo.com). All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.GPL" in the source distribution for more information.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import errno
import optparse
import os
import signal
import sys
import time

from twisted.internet import reactor

from flumotion.configure import configure
from flumotion.common import log, keycards, common, errors
from flumotion.worker import worker, config
from flumotion.twisted import credentials

def main(args):
    parser = optparse.OptionParser()
    parser.add_option('-d', '--debug',
                      action="store", type="string", dest="debug",
                      help="set debug levels")
    parser.add_option('-v', '--verbose',
                      action="store_true", dest="verbose",
                      help="be verbose")
    parser.add_option('', '--version',
                      action="store_true", dest="version",
                      default=False,
                      help="show version information")

    group = optparse.OptionGroup(parser, "worker options")
    group.add_option('-H', '--host',
                     action="store", type="string", dest="host",
                     help="manager to connect to [default localhost]")
    defaultSSLPort = configure.defaultSSLManagerPort
    defaultTCPPort = configure.defaultTCPManagerPort
    group.add_option('-P', '--port',
                     action="store", type="int", dest="port",
                     default=None,
                     help="port to listen on [default %d (ssl) or %d (tcp)]" % (defaultSSLPort, defaultTCPPort))
    group.add_option('-T', '--transport',
                     action="store", type="string", dest="transport",
                     help="transport protocol to use (tcp/ssl) [default ssl]")
    group.add_option('-n', '--name',
                     action="store", type="string", dest="name",
                     help="worker name to use in the manager")
    group.add_option('-D', '--daemonize',
                     action="store_true", dest="daemonize",
                     default=False,
                     help="run in background as a daemon")

    group.add_option('-u', '--username',
                     action="store", type="string", dest="username",
                     default="",
                     help="username to use")
    group.add_option('-p', '--password',
                     action="store", type="string", dest="password",
                     default="",
                     help="password to use, - for interactive")

    group.add_option('-F', '--feederports',
                     action="store", type="string", dest="feederports",
                     default=None,
                     help="range of feeder ports to use")

    parser.add_option_group(group)
    
    log.debug('worker', 'Parsing arguments (%r)' % ', '.join(args))
    options, args = parser.parse_args(args)

    # translate feederports string to range
    if options.feederports:
        if not '-' in options.feederports:
            raise errors.OptionError("feederports '%s' does not contain '-'" %
                options.feederports)
        (lower, upper) = options.feederports.split('-')
        options.feederports = range(int(lower), int(upper) + 1)
        log.debug('worker', 'Setting feederports %r' % options.feederports)

 
    # check if a config file was specified; if so, parse config and copy over
    if len(args) > 1:
        workerFile = args[1]
        log.info('worker', 'Reading configuration from %s' % workerFile)
        cfg = config.WorkerConfigXML(workerFile)

        # now copy over stuff from config that is not set yet
        if not options.name and cfg.name:
            log.debug('worker', 'Setting worker name %s' % cfg.name)
            options.name = cfg.name

        # manager
        if not options.host and cfg.manager.host:
            options.host = cfg.manager.host
            log.debug('worker', 'Setting manager host to %s' % options.host)
        if not options.port and cfg.manager.port:
            options.port = cfg.manager.port
            log.debug('worker', 'Setting manager port to %s' % options.port)
        if not options.transport and cfg.manager.transport:
            options.transport = cfg.manager.transport
            log.debug('worker', 'Setting manager transport to %s' %
                options.transport)

        # authentication
        if not options.username and cfg.authentication.username:
            options.username = cfg.authentication.username
            log.debug('worker', 'Setting username %s' % options.username)
        if not options.password and cfg.authentication.password:
            options.password = cfg.authentication.password
            log.debug('worker',
                'Setting password [%s]' % ("*" * len(options.password)))

        # feederports: list of allowed ports
        if not options.feederports and cfg.feederports:
            options.feederports = cfg.feederports
            log.debug('worker', 'Setting feederports %r' % options.feederports)

        # general
        if not options.debug and cfg.fludebug:
            options.debug = cfg.fludebug
        
    # set default values for all unset options
    if not options.host:
        options.host = 'localhost'
    if not options.transport:
        options.transport = 'ssl'
    if not options.port:
        if options.transport == "tcp":
            options.port = defaultTCPPort
        elif options.transport == "ssl":
            options.port = defaultSSLPort

    if not options.name:
        if options.host == 'localhost':
            options.name = 'localhost'
        else:
            import socket
            options.name = socket.gethostname()

    if not options.feederports:
        options.feederports = configure.defaultGstPortRange

    # check for wrong options/arguments
    if not options.transport in ['ssl', 'tcp']:
        sys.stderr.write('ERROR: wrong transport %s, must be ssl or tcp\n' %
            options.transport)
        return 1

    # handle all options
    if options.version:
        print common.version("flumotion-worker")
        return 0

    if options.verbose:
        log.setFluDebug("*:3")

    if options.debug:
        log.setFluDebug(options.debug)

    if options.daemonize:
        common.ensureDir(configure.logdir, "log file")
        common.ensureDir(configure.rundir, "run file")

        logPath = os.path.join(configure.logdir, 'worker.%s.log' %
            options.name)
        common.daemonize(stdout=logPath, stderr=logPath)
        log.info('worker', 'Started daemon')

        # from now on I should keep running until killed, whatever happens
        log.debug('worker', 'writing pid file')
        common.writePidFile('worker', options.name)

    # create a brain and have it remember the manager to direct jobs to
    brain = worker.WorkerBrain(options)

    # connect the brain to the manager
    if options.transport == "tcp":
        reactor.connectTCP(options.host, options.port,
            brain.worker_client_factory)
    elif options.transport == "ssl":
        from twisted.internet import ssl
        reactor.connectSSL(options.host, options.port,
            brain.worker_client_factory,
            ssl.ClientContextFactory())

    log.info('worker',
             'Connecting to manager %s:%d using %s' % (options.host,
                                                       options.port,
                                                       options.transport.upper()))

    keycard = keycards.KeycardUACPP(options.username, options.password,
                                    'localhost')
    keycard.avatarId = options.name
    brain.login(keycard)

    # the reactor needs to be able to reap its own children
    # but we also want ours reaped
    # so we install our own signal handler that first chains to twisted's,
    # then reaps children
    reactor.addSystemEventTrigger('after', 'startup',
        brain.installSIGCHLDHandler)
    reactor.addSystemEventTrigger('after', 'startup',
        brain.installSIGTERMHandler)
    log.debug('worker', 'Starting reactor')
    # FIXME: sort-of-ugly, but twisted recommends globals, and this is as
    # good as a global
    reactor.killed = False
    reactor.run()

    # for now, if we are a daemon, we keep living until we get killed
    # obviously it'd be nicer to handle error conditions that involve startup
    # better, or be reconnecting, or something, instead of sleeping forever.
    if options.daemonize and not reactor.killed:
        log.info('worker', 'Since I am a daemon, I will sleep until killed')
        common.waitForKill()
        log.info('worker', 'I was killed so I wake up')

    log.debug('worker', 'Reactor stopped')

    pids = [kid.getPid() for kid in brain.kindergarten.getKids()]
    
    log.debug('worker', 'Waiting for jobs to finish (pids %r)' % pids)
    while pids:
        try:
            pid = os.wait()[0]
        except OSError, e:
            if e.errno == errno.ECHILD:
                log.warning('worker',
                    'No children left, but list of pids is %r' % pids)
                break
            else:
                raise
        
        log.debug('worker', 'Job with pid %d finished' % pid)
        pids.remove(pid)

    if options.daemonize:
        log.debug('worker', 'deleting pid file')
        common.deletePidFile('worker', options.name)

    log.info('worker', 'All jobs finished, stopping worker')

    return 0
