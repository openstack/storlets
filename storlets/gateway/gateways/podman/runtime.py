# Copyright (c) 2023 NTT DATA Group
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

import podman
import podman.errors

from storlets.gateway.common.exceptions import StorletRuntimeException
from storlets.gateway.gateways.container.runtime import RunTimeSandbox


class PodmanRunTimeSandbox(RunTimeSandbox):

    def __init__(self, scope, conf, logger):
        super(PodmanRunTimeSandbox, self).__init__(scope, conf, logger)
        self.socket_path = conf.get('socket_path')

    def _restart(self, container_image_name):
        """
        Restarts the scope's sandbox using the specified container image

        :param container_image_name: name of the container image to start
        :raises StorletRuntimeException: when failed to restart the container
        """
        container_name = self._get_container_name(container_image_name)

        env = None
        if self.socket_path:
            env = os.environ
            env['CONTAINER_HOST'] = "unix://" + self.socket_path

        try:
            client = podman.from_env(environment=env)

            # Stop the existing storlet container
            try:
                scontainer = client.containers.get(container_name)
            except podman.errors.NotFound:
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
                command=self._get_container_command(container_name),
                entrypoint=self._get_container_entrypoint(),
                environment=self._get_container_environment(),
                name=container_name, network_mode='none',
                mounts=self._get_mounts(), userns_mode='keep-id',
                auto_remove=True, stop_signal=1,
                cpu_period=self.container_cpu_period,
                cpu_quota=self.container_cpu_quota,
                mem_limit=self.container_mem_limit,
                cpuset_cpus=self.container_cpuset_cpus,
                cpuset_mems=self.container_cpuset_mems,
                pids_limit=self.container_pids_limit,
                labels={'managed_by': 'storlets'})
        except podman.errors.ImageNotFound:
            msg = "Image %s is not found" % container_image_name
            raise StorletRuntimeException(msg)
        except podman.errors.APIError:
            self.logger.exception("Failed to manage podman containers")
            raise StorletRuntimeException("Podman runtime error")
