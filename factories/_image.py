# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util, steps
from buildbot.steps import master, worker
from buildbot.process.properties import Interpolate

from twisted.internet import defer

import buildbot
import datetime

__all__ = [
    'ImageBuildFactory',
]


def IsCacheDisabled(step):
    return not step.build.getProperty('cache', True)


class ImagePropertiesStep(steps.BuildStep):
    def __init__(self, **kwargs):
        steps.BuildStep.__init__(self, **kwargs)
        self.logEnviron = False

    def run(self):
        product = 'lirios'
        arch = 'x86_64'
        today = datetime.date.today().strftime('%Y%m%d')

        self.setProperty('product', product, self.name, runtime=True)
        self.setProperty('arch', arch, self.name, runtime=True)
        self.setProperty('imgname', '{}-{}-{}'.format(product, today, arch), self.name, runtime=True)
        self.setProperty('isofilename', '{}-{}-{}.iso'.format(product, today, arch), self.name, runtime=True)
        self.setProperty('checksumfilename', '{}-{}-{}-CHECKSUM'.format(product, today, arch), self.name, runtime=True)

        return buildbot.process.results.SUCCESS


class ImageBuildFactory(util.BuildFactory):
    """
    Build factory for ISO images.
    """

    def __init__(self, *args, **kwargs):
        util.BuildFactory.__init__(self, *args, **kwargs)

        title = 'Liri OS'
        releasever = '29'

        self.addSteps([
            ImagePropertiesStep(name='set properties'),
            steps.ShellCommand(
                name='update container',
                haltOnFailure=True,
                command=['dnf', 'update', '-y'],
            ),
            steps.ShellCommand(
                name='install tools',
                haltOnFailure=True,
                command=['dnf', 'install', '-y', 'git', 'spin-kickstarts', 'pykickstart', 'livecd-tools'],
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
            steps.ShellCommand(
                name='ksflatten',
                haltOnFailure=True,
                command=['ksflatten', Interpolate('--config=%(prop:product)s-livecd.ks'), '-o', 'livecd.ks'],
            ),
            steps.RemoveDirectory(
                name='clean cache',
                dir='/build/cache',
                doStepIf=IsCacheDisabled,
            ),
            steps.ShellCommand(
                name='build image',
                haltOnFailure=True,
                timeout=60*60,
                command=[
                    'livecd-creator', '--releasever=' + releasever,
                    '--config=livecd.ks', Interpolate('--fslabel=%(prop:imgname)s'),
                    '--title', title, Interpolate('--product=%(prop:product)s'),
                    '--cache=/build/cache'
                ],
            ),
            steps.ShellCommand(
                name='checksum',
                haltOnFailure=True,
                command=['bash', '-c', Interpolate('sha256sum -b --tag %(prop:isofilename)s > /repo/images/nightly/%(prop:checksumfilename)s')],
            ),
            steps.ShellCommand(
                name='move file',
                command=['mv', Interpolate('%(prop:isofilename)s'), '/repo/images/nightly/'],
            ),
            steps.ShellCommand(
                name='remove old images',
                command=['bash', '-c', 'find /repo/images/nightly -type f -mtime +7 -exec rm {} \;'],
            )
        ])
