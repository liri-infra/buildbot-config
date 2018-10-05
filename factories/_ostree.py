# -*- python -*-
# ex: set filetype=python:

from buildbot.process import remotecommand
from buildbot.plugins import util, steps
from buildbot.steps.worker import CompositeStepMixin
from buildbot import locks
from twisted.internet import defer

import buildbot
import os.path

__all__ = [
    'OSTreeFactory',
]


class OSTreeBuildStep(steps.BuildStep, CompositeStepMixin):
    """
    Creates the OSTree repo if needed.
    """
    def __init__(self, treefile=None, **kwargs):
        self.treefile = treefile
        steps.BuildStep.__init__(self, haltOnFailure=True, **kwargs)

    @defer.inlineCallbacks
    def run(self):
        # Initialize OS tree
        statCmd = remotecommand.RemoteCommand('stat', {'file': 'build-repo'})
        yield self.runCommand(statCmd)
        if statCmd.didFail():
            mkdirCmd = remotecommand.RemoteCommand('mkdir', {'dir': 'build-repo'})
            yield self.runCommand(mkdirCmd)
            if mkdirCmd.didFail():
                defer.returnValue(buildbot.process.results.FAILURE)
            else:
                cmd = ['ostree', 'init', '--repo=build-repo', '--mode=bare-user']
                initCmd = remotecommand.RemoteCommand('shell', {'command': cmd})
                defer.returnValue(self.convertResult(initCmd))
        # Make tree
        cmd = ['rpm-ostree', 'tree', '--repo=build-repo', '--cachedir=/build/cache', self.treefile]
        makeCmd = remotecommand.RemoteCommand('shell', {'command': cmd})
        defer.returnValue(self.convertResult(makeCmd))


class OSTreeFactory(util.BuildFactory):
    """
    Build factory for rpm-ostree OS trees.
    """
    def __init__(self, channel=None, treename=None, arch=None, *args, **kwargs):
        self.channel = channel
        self.treename = treename
        self.arch = arch
        util.BuildFactory.__init__(self, *args, **kwargs)
        self.addSteps([
            steps.ShellCommand(
                name='install tools',
                haltOnFailure=True,
                command=['dnf', 'install', '-y', 'git', 'rpm-ostree'],
            ),
            steps.Git(
                name='checkout sources',
                codebase=util.Property('codebase'),
                repourl=util.Property('repository'),
                branch=util.Property('branch'),
                mode='incremental',
                submodules=True,
                shallow=True,
            ),
            OSTreeBuildStep(name='create OS tree', treefile='lirios-{}-{}.json'.format(self.channel, self.treename)),
        ])
