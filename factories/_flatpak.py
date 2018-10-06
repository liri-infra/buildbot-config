# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util, steps

import buildbot
import os

__all__ = [
    'FlatpakFactory',
]


class FlatpakGPGStep(steps.BuildStep):
    """
    This step imports the GPG keys.
    """

    def run(self):
        self.build.addStepsAfterCurrentStep([
            steps.FileDownload(
                name='download gpg archive',
                haltOnFailure=True,
                mastersrc='flatpak/flatpak-gpg.tar.gz',
                workerdest='flatpak-gpg.tar.gz',
            ),
            steps.ShellSequence(
                name='expand gpg archive',
                haltOnFailure=True,
                logEnviron=False,
                commands=[
                    util.ShellArg(command=['tar', 'xf', 'flatpak-gpg.tar.gz'], logfile='stdio'),
                    util.ShellArg(command=['rm', '-f', 'flatpak-gpg.tar.gz'], logfile='stdio'),
                    util.ShellArg(command=['gpg2', '--homedir', 'flatpak-gpg', '--list-keys'], logfile='stdio'),
                ],
            ),
        ])
        return buildbot.process.results.SUCCESS


class FlatpakSyncStep(steps.BuildStep):
    """
    This step archives the state directory and repository,
    then publish the repository.
    """

    def run(self):
        self.build.addStepsAfterCurrentStep([
            steps.ShellSequence(
                name='archive',
                haltOnFailure=True,
                logEnviron=False,
                commands=[
                    util.ShellArg(command=['tar', 'cf', 'state-dir.tar', '.flatpak-builder'], logfile='stdio'),
                    util.ShellArg(command=['tar', 'cf', 'repo.tar', 'repo'], logfile='stdio'),
                ],
            ),
            steps.FileUpload(
                name='upload state-dir.tar',
                haltOnFailure=True,
                workersrc='state-dir.tar',
                masterdest='flatpak/state-dir.tar',
            ),
            steps.FileUpload(
                name='upload repo.tar',
                haltOnFailure=True,
                workersrc='repo.tar',
                masterdest='flatpak/repo.tar',
            ),
            steps.MasterShellCommand(
                name='sync repo',
                haltOnFailure=True,
                logEnviron=False,
                command=['./scripts/flatpak-repo.sh'],
            ),
        ])
        return buildbot.process.results.SUCCESS


class FlatpakPullStep(steps.BuildStep):
    """
    This step unpacks state directory and repository
    from master.
    """

    def run(self):
        def does_state_tar_exist(step):
            return os.path.exists('flatpak/state-dir.tar')

        def does_repo_tar_exist(step):
            return os.path.exists('flatpak/repo.tar')

        def does_exist(step):
            return does_state_tar_exist(step) and does_repo_tar_exist(step)

        self.build.addStepsAfterCurrentStep([
            steps.FileDownload(
                name='download state-dir.tar',
                haltOnFailure=True,
                doStepIf=does_state_tar_exist,
                mastersrc='flatpak/state-dir.tar',
                workerdest='state-dir.tar',
            ),
            steps.FileDownload(
                name='download repo.tar',
                haltOnFailure=True,
                doStepIf=does_repo_tar_exist,
                mastersrc='flatpak/repo.tar',
                workerdest='repo.tar',
            ),
            steps.ShellSequence(
                name='unpack archives and clean up',
                haltOnFailure=True,
                doStepIf=does_exist,
                logEnviron=False,
                commands=[
                    util.ShellArg(command=['tar', 'xf', 'state-dir.tar', 'repo.tar'], logfile='stdio'),
                    util.ShellArg(command=['rm', '-f', 'state-dir.tar', 'repo.tar'], logfile='stdio'),
                ],
            ),
        ])
        return buildbot.process.results.SUCCESS


class FlatpakRefStep(steps.BuildStep):
    """
    This step copies .flatpakref files to the master.
    """

    def __init__(self, channel=None, **kwargs):
        self.channel = channel
        steps.BuildStep.__init__(self, **kwargs)

    def run(self):
        self.build.addStepsAfterCurrentStep([
            steps.MasterShellCommand(
                name='create flatpakref directory',
                haltOnFailure=True,
                logEnviron=False,
                command=['mkdir', '-p', '/repo/flatpak/files/' + self.channel],
            ),
            steps.MasterShellCommand(
                name='remove old flatpakref files',
                haltOnFailure=True,
                logEnviron=False,
                command=['rm', '-f', '/repo/flatpak/files/%s/*.flatpakref' % self.channel],
            ),
            steps.FileUpload(
                name='upload flatpakref files',
                haltOnFailure=True,
                workersrc='%s/*.flatpakref' % self.channel,
                masterdest='/repo/flatpak/files/' + self.channel,
            ),
        ])
        return buildbot.process.results.SUCCESS


class FlatpakFactory(util.BuildFactory):
    """
    Build factory for Flatpak.
    """

    def __init__(self, channel, options, *args, **kwargs):
        channel_filename = 'channel-%s.yaml' % channel
        util.BuildFactory.__init__(self, *args, **kwargs)
        self.addSteps([
            steps.ShellCommand(
                name='install tools',
                haltOnFailure=True,
                logEnviron=False,
                command=['sudo', 'dnf', 'install', '-y', 'flatpak', 'flatpak-builder', 'python3-PyYAML'],
            ),
            FlatpakGPGStep(name='setup gpg keys'),
            steps.Git(
                name='checkout sources',
                codebase=util.Property('codebase'),
                repourl=util.Property('repository'),
                branch=util.Property('branch'),
                mode='incremental',
                submodules=True,
                shallow=True,
            ),
            FlatpakPullStep(name='pull from master'),
            steps.ShellCommand(
                name='build',
                haltOnFailure=True,
                command=['./flatpak-build', '--repo=repo', '--channel=' + channel_filename, '--jobs=1', '--export', '--gpg-homedir=flatpak-gpg', '--gpg-sign=' + options['gpg-key']],
            ),
            FlatpakRefStep(name='copy flatpakref files', channel=channel),
            FlatpakSyncStep(name='sync repo'),
        ])
