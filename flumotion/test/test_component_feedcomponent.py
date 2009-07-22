# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2009 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

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

from flumotion.common.testsuite import TestCase
from flumotion.component import feedcomponent
from twisted.internet import defer


class FakeComponent(feedcomponent.ParseLaunchComponent):
    pass


class FeedComponentMedium(feedcomponent.FeedComponentMedium):

    # Override connectEater to test #1277
    # We don't need most of the things
    # connectEater does to verify #1277
    # For now let's return a deferred
    # object here like it usually does

    def connectEater(self, eaterAlias):
        d = defer.Deferred()
        d.callback(None)
        return d


class TestFeedComponentMedium(TestCase):

    def setUp(self):
        config = {}
        config['name'] = "FakeComponent"
        self._fakecomp = FakeComponent(config)
        self._feedcompmed = FeedComponentMedium(self._fakecomp)

    def tearDown(self):
        self._fakecomp.stop()

    def testRemoteEatFrom(self):
        eaterAlias = "default"
        fullFeedId = "/default/fake-component:default"
        host = "127.0.0.1"
        port = 8080
        self._feedcompmed.remote_eatFrom(eaterAlias,
                                         fullFeedId,
                                         host,
                                         port)

        # Reconnect when given a new feed
        fullFeedId = "/default/dummy-component:default"
        host = "192.168.3.8"
        port = 8081
        rs = self._feedcompmed.remote_eatFrom(eaterAlias,
                                              fullFeedId,
                                              host,
                                              port)
        self.assertNotEqual(None, rs)

    def test1277(self):
        eaterAlias = "default",
        fullFeedId = "/default/fake-component:default"
        host = "127.0.0.1"
        port = 8080
        self._feedcompmed.remote_eatFrom(eaterAlias,
                                         fullFeedId,
                                         host,
                                         port)

        # Now issue eatFrom again with the same feed
        # The correct behavior is for it to ignore
        # the request and return None
        rs = self._feedcompmed.remote_eatFrom(eaterAlias,
                                              fullFeedId,
                                              host,
                                              port)
        self.failUnlessEqual(None, rs)