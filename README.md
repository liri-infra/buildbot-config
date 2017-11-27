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
