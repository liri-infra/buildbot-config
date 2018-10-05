# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util, steps

import datetime

__all__ = [
    'ImageBuildFactory',
]


class ImageBuildFactory(util.BuildFactory):
    """
    Build factory for ISO images.
    """

    def __init__(self, *args, **kwargs):
        util.BuildFactory.__init__(self, *args, **kwargs)

        today = datetime.date.today().strftime('%Y%m%d')
        title = 'Liri OS'
        product = 'lirios'
        releasever = '28'
        imgname = '%s-%s-x86_64' % (product, today)
        isofilename = imgname + '.iso'
        checksumfilename = imgname + '-CHECKSUM'

        self.addSteps([
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
                command=['ksflatten', '--config=%s-livecd.ks' % product, '-o', 'livecd.ks'],
            ),

            steps.ShellCommand(
                name='build image',
                haltOnFailure=True,
                command=[
                    'livecd-creator', '--releasever=' + releasever,
                    '--config=livecd.ks', '--fslabel=' + imgname,
                    '--title', title, '--product=' + product,
                    '--cache=/build/cache'
                ],
            ),
            steps.ShellCommand(
                name='checksum',
                haltOnFailure=True,
                command=['bash', '-c', 'sha256sum -b --tag %s > /repo/images/nightly/%s' % (isofilename, checksumfilename)],
            ),
            steps.ShellCommand(
                name='move file',
                command=['mv', isofilename, '/repo/images/nightly/'],
            ),
            steps.ShellCommand(
                name='remove old images',
                command=['bash', '-c', 'find /repo/images/nightly -type f -mtime +7 -exec rm {} \;'],
            )
        ])
