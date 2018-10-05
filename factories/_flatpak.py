# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util, steps

__all__ = [
    'FlatpakFactory',
]


class FlatpakFactory(util.BuildFactory):
    """
    Build factory for Flatpak.
    """

    def __init__(self, metadata, gpg_key, *args, **kwargs):
        util.BuildFactory.__init__(self, *args, **kwargs)
        repo_path = '/build/repo'
        self.addSteps([
            steps.ShellCommand(
                name='import private gpg key',
                haltOnFailure=True,
                command=['sudo', 'gpg', '--import', '/build/key.gpg'],
                workdir=self.workdir,
            ),
            steps.ShellCommand(
                name='list gpg keys',
                haltOnFailure=True,
                command=['sudo', 'gpg', '--list-keys'],
                workdir=self.workdir,
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
                name='build runtime',
                haltOnFailure=True,
                command=['sudo', './flatpak-build', '--repo=' + repo_path, 'build', '--metadata=' + metadata, '--type=runtime', '--gpg-key=' + gpg_key],
                workdir=self.workdir,
            ),
            steps.ShellCommand(
                name='export',
                haltOnFailure=True,
                command=['sudo', './flatpak-build', 'export', '--gpg-key=' + gpg_key],
                workdir=self.workdir,
            ),
            steps.ShellCommand(
                name='build apps',
                haltOnFailure=True,
                command=['sudo', './flatpak-build', '--repo=' + repo_path, 'build', '--metadata=' + metadata, '--type=app', '--gpg-key=' + gpg_key],
                workdir=self.workdir,
            ),
            steps.ShellCommand(
                name='synchronize to repo',
                haltOnFailure=True,
                command=['sudo', './flatpak-build', 'sync', '--dest=/flatpak/repo'],
                workdir=self.workdir,
            ),
            steps.ShellCommand(
                name='create runtime files',
                haltOnFailure=True,
                command=['sudo', './flatpak-build', 'files', '--metadata=' + metadata, '--type=runtime', '--gpg-key=' + gpg_key, '--dest=/flatpak/files'],
                workdir=self.workdir,
            ),
            steps.ShellCommand(
                name='create apps files',
                haltOnFailure=True,
                command=['sudo', './flatpak-build', 'files', '--metadata=' + metadata, '--type=app', '--gpg-key=' + gpg_key, '--dest=/flatpak/files'],
                workdir=self.workdir,
            ),
        ])
