# Copyright (c) 2015, 2016 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import docker
import docker.errors
from docker.types import Mount as DockerMount

from storlets.gateway.common.exceptions import StorletRuntimeException
from storlets.gateway.gateways.container.runtime import RunTimeSandbox


class DockerRunTimeSandbox(RunTimeSandbox):

    def _restart(self, container_image_name):
        """
        Restarts the scope's sandbox using the specified container image

        :param container_image_name: name of the container image to start
        :raises StorletRuntimeException: when failed to restart the container
        """
        if self.container_image_namespace:
            container_image_name = '%s/%s' % (self.container_image_namespace,
                                              container_image_name)

        container_name = '%s_%s' % (self.container_image_name_prefix,
                                    self.scope)

        mounts = [
            DockerMount('/dev/log', '/dev/log', type='bind'),
            DockerMount(self.paths.sandbox_pipe_dir,
                        self.paths.host_pipe_dir,
                        type='bind'),
            DockerMount(self.paths.sandbox_storlet_base_dir,
                        self.paths.host_storlet_base_dir,
                        type='bind'),
            DockerMount(self.paths.sandbox_storlet_native_lib_dir,
                        self.paths.host_storlet_native_lib_dir,
                        type='bind', read_only=True),
            DockerMount(self.paths.sandbox_storlet_native_bin_dir,
                        self.paths.host_storlet_native_bin_dir,
                        type='bind', read_only=True)
            ]

        try:
            client = docker.from_env()
            # Stop the existing storlet container
            try:
                scontainer = client.containers.get(container_name)
            except docker.errors.NotFound:
                # The container is not yet created
                pass
            else:
                scontainer.stop(timeout=self.sandbox_stop_timeout)

            # Check whether a new container can be started
            if self.max_containers_per_node > 0:
                all_scontainers = client.containers.list(
                    filters={'label': 'managed_by=storlets'})
                if len(all_scontainers) >= self.max_containers_per_node:
                    raise StorletRuntimeException(
                        "Cannot start a container because of limit")

            # Start the new one
            client.containers.run(
                container_image_name, detach=True,
                command=[
                    self.paths.sandbox_factory_pipe,
                    self.storlet_daemon_factory_debug_level,
                    container_name
                ],
                entrypoint=[
                    os.path.join(
                        self.paths.sandbox_storlet_native_bin_dir,
                        'storlets-daemon-factory'
                    )
                ],
                environment={
                    'PYTHONPATH': os.path.join(
                        self.paths.sandbox_storlet_native_lib_dir, 'python'
                    )
                },
                name=container_name, network_disabled=True,
                mounts=mounts, user=os.getuid(),
                auto_remove=True, stop_signal='SIGHUP',
                cpu_period=self.container_cpu_period,
                cpu_quota=self.container_cpu_quota,
                mem_limit=self.container_mem_limit,
                cpuset_cpus=self.container_cpuset_cpus,
                cpuset_mems=self.container_cpuset_mems,
                pids_limit=self.container_pids_limit,
                labels={'managed_by': 'storlets'})
        except docker.errors.ImageNotFound:
            msg = "Image %s is not found" % container_image_name
            raise StorletRuntimeException(msg)
        except docker.errors.APIError:
            self.logger.exception("Failed to manage docker containers")
            raise StorletRuntimeException("Docker runtime error")
