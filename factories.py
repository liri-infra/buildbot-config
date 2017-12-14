# -*- python -*-
# ex: set filetype=python:

from buildbot.process.build import Build
from buildbot.plugins import *
from buildbot.steps.worker import CompositeStepMixin
from buildbot import locks
from twisted.python import log
from twisted.internet import defer

import buildbot
import os.path
import json

from liribotcfg import utils

def shellArgOptional(commands):
    return util.ShellArg(logfile='stdio', command=commands)


def shellArg(commands):
    return util.ShellArg(logfile='stdio', haltOnFailure=True, command=commands)


# We create one worker lock per build-id, which is the same as the workdir
# so multiple builds never work in the same workdir on any particular worker
class BuildIDLockBuild(Build):
    _workerLocks = {}

    @staticmethod
    def find_or_create_master_lock_for_buildid(buildid):
        lock = BuildIDLockBuild._workerLocks.get(buildid)
        if lock is None:
            log.msg("********* Created lock for buildid %s" % buildid)
            lock = locks.WorkerLock(buildid + ' buildid lock')
            BuildIDLockBuild._workerLocks[buildid] = lock
        return lock

    def startBuild(self, build_status, workerforbuilder):
        buildid = self.getProperty('liribuilder-build-id')
        lock = BuildIDLockBuild.find_or_create_master_lock_for_buildid(buildid)
        self.setLocks([lock.access('exclusive'), flatpak_worker_lock.access('counting')])
        return Build.startBuild(self, build_status, workerforbuilder)


class ArchLinuxBuildStep(steps.BuildStep, CompositeStepMixin):
    """
    Build step to build the ArchLinux packages.
    """

    def __init__(self, triggers=None, **kwargs):
        steps.BuildStep.__init__(self, haltOnFailure=True, **kwargs)

    @defer.inlineCallbacks
    def run(self):
        builddir = self.build.properties.getProperty('builddir')
        content = yield self.getFileContentFromWorker('channels.json')
        if content is None:
            channels = {'stable': [], 'unstable': []}
        else:
            channels = utils.json_to_ascii(json.loads(content))
        for name in channels['unstable']:
            self.build.addStepsAfterLastStep([
                steps.ShellCommand(
                    name='build ' + name,
                    haltOnFailure=True,
                    command=['../docker-build'],
                    workdir=os.path.join(self.workdir, name),
                )
            ])
        defer.returnValue(buildbot.process.results.SUCCESS)


class ArchPackagesBuildFactory(util.BuildFactory):
    """
    Build factory for ArchLinux packages.
    """

    def __init__(self, *args, **kwargs):
        util.BuildFactory.__init__(self, *args, **kwargs)
        #self.buildClass = BuildIDLockBuild
        #self.workdir = util.Property('liribuilder-build-id')
        self.addSteps([
            steps.Git(
                name='checkout sources',
                codebase=util.Property('codebase'),
                repourl=util.Property('repository'),
                branch=util.Property('branch'),
                mode='incremental',
                submodules=True,
                shallow=True,
            ),
            ArchLinuxBuildStep(name='select packages'),
            steps.POST(
                name='trigger rebuild lirios/unstable',
                url='https://registry.hub.docker.com/u/lirios/unstable/trigger/9b83357b-10ff-4c61-9665-9f203e2cc793/',
                headers={'Content-type': 'application/json'},
                data={'build': True}
            )
        ])


class ArchISOBuildFactory(util.BuildFactory):
    """
    Build factory for ArchLinux ISO images.
    """

    def __init__(self, *args, **kwargs):
        util.BuildFactory.__init__(self, *args, **kwargs)
        self.addSteps([
            steps.Git(
                name='checkout sources',
                codebase=util.Property('codebase'),
                repourl=util.Property('repository'),
                branch=util.Property('branch'),
                mode='incremental',
                submodules=True,
                shallow=True,
            ),
            steps.ShellCommand(
                name='build image',
                haltOnFailure=True,
                command=['sudo', './build.sh', '-v', '-o', '/repo/images/nightly/'],
                workdir=os.path.join(self.workdir, 'livecd'),
            ),
            steps.ShellCommand(
                name='clean up',
                command=['sudo', 'rm', '-rf', 'work'],
                workdir=os.path.join(self.workdir, 'livecd'),
            ),
        ])


class DockerHubBuildFactory(util.BuildFactory):
    """
    Build factory that triggers a rebuild of the Docker
    images used by this continous integration.
    """
    def __init__(self, triggers, tags, *args, **kwargs):
        util.BuildFactory.__init__(self, *args, **kwargs)
        steps_list = []
        for info in triggers:
            build = False
            available_tags = info.get('tags', [])
            for tag in tags:
                if tag in available_tags:
                    build = True
            if build is True:
                url = 'https://registry.hub.docker.com/u/%(name)s/trigger/%(token)s/' % info
                steps_list.append(steps.POST(name='trigger rebuild %(name)s' % info, url=url, headers={'Content-type': 'application/json'}, data={'build': True}))
        if len(steps_list) > 0:
            self.addSteps(steps_list)
