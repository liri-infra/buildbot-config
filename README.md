# Buildbot configuration

This is the [Buildbot](http://buildbot.net/) configuration for Liri.

It is deployed with the `buildbot/buildbot-master` Docker container (https://hub.docker.com/r/buildbot/buildbot-master/)
cloning this repository inside a directory called `liribotcfg` and linking `master.cfg` to the upper level directory.

Something like:

```sh
git clone https://github.com/lirios/buildbot.git liribotcfg
ln -s liribotcfg/master.cfg
```

The deployment is like [metabotcfg](https://github.com/buildbot/metabbotcfg).

## Deployment

Create a directory, create `config.json` inside it and then
run the container:

```sh
# from the directory with config.json in it
sudo docker run -i -t --rm \
    -v $(pwd):/var/lib/buildbot/settings:ro \
    -v /srv/ci/buildbot:/data \
    -e BUILDBOT_CONFIG_URL=https://github.com/lirios/buildbot-config/archive/master.tar.gz \
    -e BUILDBOT_CONFIG_DIR=liribotcfg buildbot/buildbot-master
```
