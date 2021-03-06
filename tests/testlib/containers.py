#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
import tarfile
import logging
import subprocess
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Optional  # pylint: disable=unused-import
import requests

import dockerpty  # type: ignore[import]
import docker  # type: ignore[import]

import testlib
from testlib.version import CMKVersion

_DOCKER_REGISTRY = "artifacts.lan.tribe29.com:4000"
_DOCKER_REGISTRY_URL = "https://%s/v2/" % _DOCKER_REGISTRY
_DOCKER_IMAGE = "%s/ubuntu-19.04-os-image" % _DOCKER_REGISTRY

logger = logging.getLogger()


def execute_tests_in_container(version, result_path, command, interactive):
    # type: (CMKVersion, Path, List[str], bool) -> int
    client = _docker_client()
    info = client.info()
    logger.info("Docker version: %s", info["ServerVersion"])

    # When invoking the test based on the current git, use the container based on
    # the current daily build. The git is patched into that version later in the
    # test container

    # TODO: Why don't we use our official containers here? We should have all the code
    # ready for using it in either "docker" or "tests-py3/docker" directory.
    image_name = _create_cmk_image(client, _DOCKER_IMAGE, version)

    # Start the container
    with _start(
            client,
            image=image_name,
            command="/bin/bash",
            volumes=list(_runtime_volumes().keys()),
            host_config=client.api.create_host_config(
                # Create some init process that manages signals and processes
                init=True,
                # needed to make the overlay mounts work on the /git directory
                # Should work, but does not seem to be enough: 'cap_add=["SYS_ADMIN"]'. Using this instead:
                privileged=True,
                # Important to workaround really high default of docker which results
                # in problems when trying to close all FDs in Python 2.
                ulimits=[
                    docker.types.Ulimit(name="nofile", soft=1024, hard=1024),
                ],
                binds=[":".join([k, v["bind"], v["mode"]]) for k, v in _runtime_volumes().items()],
            ),
            stdin_open=True,
            tty=True,
    ) as container:
        # Ensure we can make changes to the git directory (not persisting it outside of the container)
        _prepare_git_overlay(container, "/git-lowerdir", "/git")
        _reuse_persisted_virtual_environment(container, version)

        if interactive:
            logger.info("+-------------------------------------------------")
            logger.info("| Next steps:")
            logger.info("| ")
            logger.info("| /git/scripts/run-pipenv 3 shell")
            logger.info("| cd /git")
            logger.info("| ")
            logger.info("| ... start whatever test you want, for example:")
            logger.info("| ")
            logger.info("| make -C tests-py3 test-integration")
            logger.info("| ")
            logger.info("|   Execute all integration tests")
            logger.info("| ")
            logger.info("| tests-py3/scripts/run-integration-test.py "
                        "tests/integration/livestatus/test_livestatus.py")
            logger.info("| ")
            logger.info("|   Execute some integration tests")
            logger.info("| ")
            logger.info("| tests-py3/scripts/run-integration-test.py "
                        "tests/integration/livestatus/test_livestatus.py "
                        "-k test_service_custom_variables ")
            logger.info("| ")
            logger.info("|   Execute a single test")
            logger.info("| ")
            logger.info("+-------------------------------------------------")
            dockerpty.start(client.api, container.id)
            return 0

        # Now execute the real test in the container context
        exit_code = _exec_run(
            container,
            command,
            environment=_container_env(version),
            workdir="/git",
            stream=True,
        )

        # Collect the test results located in /results of the container. The
        # jenkins job will make it available as artifact later
        _copy_directory(container, Path("/results"), result_path)

        return exit_code


def _docker_client():
    return docker.from_env()


def _get_or_load_image(client, image_name):
    # type: (docker.DockerClient, str) -> Optional[docker.Image]
    try:
        image = client.images.get(image_name)
        logger.info("Image %s is already available locally (%s)", image_name, image.short_id)
        return image
    except docker.errors.ImageNotFound:
        logger.info("Image %s is not available locally, trying to download from registry",
                    image_name)

    try:
        image = client.images.pull("%s:latest" % image_name)
        logger.info("Image %s has been loaded from registry (%s)", image_name, image.short_id)
        return image
    except docker.errors.NotFound:
        logger.info("Image %s is not available from registry", image_name)
    except docker.errors.APIError as e:
        if "no basic auth" in "%s" % e:
            raise Exception(
                "No authentication information stored for %s. You will have to login to the "
                "registry using \"docker login %s\" to be able to execute the tests." %
                (_DOCKER_REGISTRY, _DOCKER_REGISTRY_URL))
        if "request canceled while waiting for connection" in "%s" % e:
            return None
        if "dial tcp: lookup " in "%s" % e:
            # May happen when offline on ubuntu
            return None
        raise

    return None


def _create_cmk_image(client, base_image_name, version):
    # type: (docker.DockerClient, str, CMKVersion) -> str
    image_name = "%s-%s-%s-%s" % (base_image_name, version.edition_short, version.version,
                                  version.branch())

    logger.info("Preparing %s image from %s", image_name, base_image_name)
    # First try to get the image from the local or remote registry
    # TODO: How to handle image updates?
    image = _get_or_load_image(client, image_name)
    if image:
        return image_name  # already found, nothing to do.

    logger.info("Create new image %s from %s", image_name, base_image_name)
    # TODO: How to handle image updates?
    base_image = _get_or_load_image(client, base_image_name)
    if base_image is None:
        raise Exception(
            "Image %s is not available locally and the registry \"%s\" is not reachable. It is "
            "not implemented yet to build the image locally. Terminating." %
            (base_image_name, _DOCKER_REGISTRY_URL))

    with _start(
            client,
            image=base_image_name,
            command=["tail", "-f", "/dev/null"],  # keep running
            volumes=list(_image_build_volumes().keys()),
            host_config=client.api.create_host_config(
                # needed to make the overlay mounts work on the /git directory
                # Should work, but does not seem to be enough: 'cap_add=["SYS_ADMIN"]'. Using this instead:
                privileged=True,
                binds=[
                    ":".join([k, v["bind"], v["mode"]]) for k, v in _image_build_volumes().items()
                ],
            ),
    ) as container:

        logger.info("Building in container %s (created from %s)", container.short_id,
                    base_image_name)

        assert _exec_run(container, ["mkdir", "-p", "/results"]) == 0

        # Ensure we can make changes to the git directory (not persisting it outside of the container)
        _prepare_git_overlay(container, "/git-lowerdir", "/git")
        _prepare_virtual_environments(container, version)
        _persist_virtual_environments(container, version)

        logger.info("Install Checkmk version")
        assert _exec_run(
            container,
            ["scripts/run-pipenv", "3", "run", "/git/tests-py3/scripts/install-cmk.py"],
            workdir="/git",
            environment=_container_env(version),
            stream=True,
        ) == 0

        logger.info("Check whether or not installation was OK")
        assert _exec_run(container, ["ls", "/omd/versions/default"], workdir="/") == 0

        logger.info("Finalizing image")

        container.stop()

        image = container.commit(image_name)
        logger.info("Commited image %s (%s)", image_name, image.short_id)

        # TODO: Push image to the registry?

    return image_name


def _image_build_volumes():
    return {
        # To get access to the test scripts and for updating the version from
        # the current git checkout. Will also be used for updating the image with
        # the current git state
        testlib.repo_path(): {
            "bind": "/git-lowerdir",
            "mode": "ro",
        },
        # Used to gather the Checkmk package from. In case it is not available
        # the package will be downloaded from the download server
        "/bauwelt/download": {
            "bind": "/bauwelt/download",
            "mode": "ro",
        },
        # Credentials file for fetching the package from the download server. Used by
        # testlib/version.py in case the version package needs to be downloaded
        os.path.join(os.environ["HOME"], ".cmk-credentials"): {
            "bind": "/root/.cmk-credentials",
            "mode": "ro",
        }
    }


def _runtime_volumes():
    return {
        # To get access to the test scripts and for updating the version from
        # the current git checkout. Will also be used for updating the image with
        # the current git state
        testlib.repo_path(): {
            "bind": "/git-lowerdir",
            "mode": "ro",
        },
        # For whatever reason the image can not be started when nothing is mounted
        # at the file mount that was used while building the image. This is not
        # really needed during runtime of the test. We could mount any file.
        os.path.join(os.environ["HOME"], ".cmk-credentials"): {
            "bind": "/root/.cmk-credentials",
            "mode": "ro",
        }
    }


def _container_env(version):
    # type: (CMKVersion) -> Dict[str, str]
    return {
        "LANG": "C",
        "PIPENV_PIPFILE": "/git/Pipfile",
        "PIPENV_VENV_IN_PROJECT": "true",
        "VERSION": version.version,
        "EDITION": version.edition_short,
        "BRANCH": version.branch(),
        "RESULT_PATH": "/results",
    }


@contextmanager
def _start(client, **kwargs):
    logger.info("Start new container from %s (Args: %s)", kwargs["image"], kwargs)

    try:
        client.images.get(kwargs["image"])
    except docker.errors.ImageNotFound:
        raise Exception("Image %s could not be found locally" % kwargs["image"])

    # Start the container with lowlevel API to be able to attach with a debug shell
    # after initialization
    container_id = client.api.create_container(**kwargs)["Id"]
    client.api.start(container_id)
    c = client.containers.get(container_id)

    logger.info("Container ID: %s", c.short_id)

    logger.info("Container is ready")

    try:
        yield c
    finally:
        c.remove(force=True)


def _exec_run(c, cmd, **kwargs):
    if kwargs:
        logger.info("Execute in container %s: %r (kwargs: %r)", c.short_id,
                    subprocess.list2cmdline(cmd), kwargs)
    else:
        logger.info("Execute in container %s: %r", c.short_id, subprocess.list2cmdline(cmd))

    result = container_exec(c, cmd, **kwargs)

    if kwargs.get("stream"):
        return result.communicate(line_prefix=b"%s: " % c.short_id.encode("ascii"))

    printed_dot = False
    while result.poll() is None:
        printed_dot = True
        sys.stdout.write(".")
    if printed_dot:
        sys.stdout.write("\n")

    return result.poll()


def container_exec(container,
                   cmd,
                   stdout=True,
                   stderr=True,
                   stdin=False,
                   tty=False,
                   privileged=False,
                   user='',
                   detach=False,
                   stream=False,
                   socket=False,
                   environment=None,
                   workdir=None):
    """
    An enhanced version of #docker.Container.exec_run() which returns an object
    that can be properly inspected for the status of the executed commands.

    Taken from https://github.com/docker/docker-py/issues/1989. Thanks!
    """

    exec_id = container.client.api.exec_create(container.id,
                                               cmd,
                                               stdout=stdout,
                                               stderr=stderr,
                                               stdin=stdin,
                                               tty=tty,
                                               privileged=privileged,
                                               user=user,
                                               environment=environment,
                                               workdir=workdir)['Id']

    output = container.client.api.exec_start(exec_id,
                                             detach=detach,
                                             tty=tty,
                                             stream=stream,
                                             socket=socket)

    return ContainerExec(container.client, exec_id, output)


class ContainerExec(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, client, container_id, output):
        self.client = client
        self.id = container_id
        self.output = output

    def inspect(self):
        return self.client.api.exec_inspect(self.id)

    def poll(self):
        return self.inspect()['ExitCode']

    def communicate(self, line_prefix=b''):
        for data in self.output:
            if not data:
                continue

            offset = 0
            while offset < len(data):
                nl = data.find(b'\n', offset)
                if nl >= 0:
                    slce = data[offset:nl + 1]
                    offset = nl + 1
                    sys.stdout.buffer.write(slce)
                    sys.stdout.buffer.write(line_prefix)
                else:
                    slce = data[offset:]
                    offset += len(slce)
                    sys.stdout.buffer.write(slce)
            sys.stdout.flush()
        while self.poll() is None:
            raise RuntimeError()
        return self.poll()


def _copy_directory(container, src_path, dest_path):
    # type: (docker.types.containers.Container, Path, Path) -> None
    logger.info("Copying %s from container to %s", src_path, dest_path)

    tar_stream = BytesIO()
    bits, _stat = container.get_archive(str(src_path))
    for chunk in bits:
        tar_stream.write(chunk)
    tar_stream.seek(0)

    tar = tarfile.TarFile(fileobj=tar_stream)
    tar.extractall(str(dest_path))


def _prepare_git_overlay(container, lower_path, target_path):
    """Prevent modification of git checkout volume contents

    Create some tmpfs that is mounted as rw layer over the the git checkout
    at /git. All modifications to the git will be lost after the container is
    removed.
    """
    logger.info("Preparing overlay filesystem for %s at %s", lower_path, target_path)
    tmpfs_path = "/git-rw"
    upperdir_path = "%s/upperdir" % tmpfs_path
    workdir_path = "%s/workdir" % tmpfs_path

    # Create mountpoints
    assert _exec_run(container, ["mkdir", "-p", tmpfs_path, target_path]) == 0

    # Prepare the tmpfs as base for the rw-overlay and workdir
    assert _exec_run(
        container,
        ["mount", "-t", "tmpfs", "tmpfs", tmpfs_path],
    ) == 0

    # Create directory structure for the overlay
    assert _exec_run(container, ["mkdir", "-p", upperdir_path, workdir_path]) == 0

    # Finally add the overlay mount
    assert _exec_run(
        container,
        [
            "mount", "-t", "overlay", "overlay", "-o",
            "lowerdir=%s,upperdir=%s,workdir=%s" %
            (lower_path, upperdir_path, workdir_path), target_path
        ],
    ) == 0


def _prepare_virtual_environments(container, version):
    """Ensure the virtual environments are ready for use

    Because the virtual environments are in the /git path (which is not persisted),
    the initialized virtual environment will be copied to /virtual-envs, which is
    persisted with the image. The test containers may use them.
    """
    _cleanup_previous_virtual_environments(container, version)
    _setup_virtual_environments(container, version)


def _setup_virtual_environments(container, version):
    logger.info("Prepare virtual environment")
    assert _exec_run(
        container,
        ["make", ".venv-3.7"],
        workdir="/git",
        environment=_container_env(version),
        stream=True,
    ) == 0

    assert _exec_run(container, ["test", "-d", "/git/virtual-envs/2.7/.venv"]) == 0
    assert _exec_run(container, ["test", "-d", "/git/virtual-envs/3.7/.venv"]) == 0


def _cleanup_previous_virtual_environments(container, version):
    # When the git is mounted to the test container for a node which already
    # created it's virtual environments these may be incompatible with the
    # containers OS. Clean up, just to be sure.
    logger.info("Cleanup previous virtual environments")
    assert _exec_run(
        container,
        ["rm", "-rf", "virtual-envs/3.7/.venv", "virtual-envs/2.7/.venv"],
        workdir="/git",
        environment=_container_env(version),
        stream=True,
    ) == 0

    assert _exec_run(container, ["test", "-n", "/virtual-envs/2.7/.venv"]) == 0
    assert _exec_run(container, ["test", "-n", "/virtual-envs/3.7/.venv"]) == 0


def _persist_virtual_environments(container, version):
    logger.info("Persisting virtual environments for later use")
    assert _exec_run(
        container,
        ["rsync", "-aR", "virtual-envs/2.7/.venv", "virtual-envs/3.7/.venv", "/"],
        workdir="/git",
        environment=_container_env(version),
        stream=True,
    ) == 0

    assert _exec_run(container, ["test", "-d", "/virtual-envs/2.7/.venv"]) == 0
    assert _exec_run(container, ["test", "-d", "/virtual-envs/3.7/.venv"]) == 0


def _reuse_persisted_virtual_environment(container, version):
    _cleanup_previous_virtual_environments(container, version)

    if _exec_run(container, ["test", "-d", "/virtual-envs"],
                 workdir="/git",
                 environment=_container_env(version)) == 0:
        logger.info("Restore previously created virtual environments")
        assert _exec_run(
            container,
            ["rsync", "-a", "/virtual-envs", "/git"],
            workdir="/git",
            environment=_container_env(version),
            stream=True,
        ) == 0

    if _mirror_reachable():
        #  Only try to update when the mirror is available, otherwise continue with the current
        #  state, which is good for the most of the time.
        _setup_virtual_environments(container, version)


def _mirror_reachable():
    try:
        requests.get(_DOCKER_REGISTRY_URL, timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False
