# -*- python -*-
# ex: set filetype=python:

from liribotcfg import utils

import json

class Configuration(object):
    def __init__(self):
        try:
            f = open('config.json', 'r')
        except IOError:
            f = open('/var/lib/buildbot/settings/config.json', 'r')
        self._config = utils.json_to_ascii(json.loads(f.read ()))

    def _get_config(self, name, default=""):
        return self._config.get(name, default)

    def _get_configv(self, name, default=[]):
        return self._config.get(name, default)

    @property
    def buildbot_port(self):
        return self._get_config('buildbot-port', 8010)

    @property
    def buildbot_uri(self):
        return self._get_config('buildbot-uri')

    @property
    def num_master_workers(self):
        return self._get_config('num-master-workers', 4)

    @property
    def admin_username(self):
        return self._get_config('admin-username')

    @property
    def admin_password(self):
        return self._get_config('admin-password')

    @property
    def github_auth_client(self):
        return self._get_config('github-auth-client')

    @property
    def github_auth_secret(self):
        return self._get_config('github-auth-secret')

    @property
    def slack_reporter(self):
        return self._get_config('slack-reporter', default={})

    @property
    def docker_workers(self):
        return self._get_config('docker-workers', default={})

    @property
    def docker_hub_triggers(self):
        return self._get_configv('docker-hub-triggers')

    @property
    def flatpak_gpg_key(self):
        return self._get_config('flatpak-gpg-key')
