# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util, steps

__all__ = [
    'DockerHubBuildFactory',
]


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
                url = 'https://cloud.docker.com/api/build/v1/source/%(uuid)s/trigger/%(token)s/call/' % info
                steps_list.append(steps.POST(name='trigger rebuild %(name)s' % info, url=url, headers={'Content-type': 'application/json'}, data={'build': True}))
        if len(steps_list) > 0:
            self.addSteps(steps_list)
