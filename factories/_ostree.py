# -*- python -*-
# ex: set filetype=python:

from buildbot.process import remotecommand, buildstep
from buildbot.plugins import util, steps
from buildbot import locks
from twisted.internet import defer

import buildbot
import os

__all__ = [
    'OSTreeFactory',
]


class OSTreeBuildStep(buildstep.ShellMixin, steps.BuildStep):
    """
    Creates the OSTree repo if needed.
    """
    def __init__(self, treefile=None, **kwargs):
        self.treefile = treefile
        self.setupShellMixin({'logEnviron': False,
                              'timeout': 3600,
                              'usePTY': True})
        steps.BuildStep.__init__(self, haltOnFailure=True, **kwargs)
        self.title = 'Create OS tree'

    @defer.inlineCallbacks
    def run(self):
        # Initialize build repo
        cmd = ['ostree', 'init', '--repo=build-repo', '--mode=bare-user']
        initCmd = yield self.makeRemoteShellCommand(command=cmd)
        yield self.runCommand(initCmd)
        if initCmd.didFail():
            defer.returnValue(buildbot.process.results.FAILURE)
            return
        # Make tree
        mkdirCmd = yield self.makeRemoteShellCommand(command=['mkdir', '-p', '../cache'])
        yield self.runCommand(mkdirCmd)
        cmd = ['sudo', 'rpm-ostree', 'compose', 'tree', '--repo=build-repo', '--cachedir=../cache', self.treefile]
        makeCmd = yield self.makeRemoteShellCommand(command=cmd)
        yield self.runCommand(makeCmd)
        defer.returnValue(makeCmd.results())


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
            steps.ShellSequence(
                name='install tools',
                haltOnFailure=True,
                logEnviron=False,
                commands=[
                    util.ShellArg(command=['sudo', 'dnf', 'update', '-y'], logfile='stdio'),
                    util.ShellArg(command=['sudo', 'dnf', 'install', '-y', 'git', 'rpm-ostree'], logfile='stdio'),
                ],
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
            steps.FileDownload(
                name='download build-repo.tar',
                haltOnFailure=False,
                mastersrc='/srv/ci/buildbot/data/ostree/build-repo.tar',
                workerdest='build-repo.tar'
            ),
            steps.ShellCommand(
                name='expand build-repo.tar',
                haltOnFailure=False,
                logEnviron=False,
                command=['tar', 'xf', 'build-repo.tar'],
            ),
            OSTreeBuildStep(name='create OS tree', treefile='lirios-{}-{}.json'.format(self.channel, self.treename)),
            steps.ShellCommand(
                name='archive build-repo',
                haltOnFailure=True,
                logEnviron=False,
                command=['tar', 'cf', 'build-repo.tar', 'build-repo'],
            ),
            steps.FileUpload(
                name='upload build-repo.tar',
                haltOnFailure=True,
                workersrc='build-repo.tar',
                masterdest='/srv/ci/buildbot/data/ostree/build-repo.tar',
            ),
            steps.ShellCommand(
                name='remove build-repo',
                haltOnFailure=False,
                logEnviron=False,
                command=['rm', '-rf', 'build-repo', 'build-repo.tar'],
            ),
        ])
