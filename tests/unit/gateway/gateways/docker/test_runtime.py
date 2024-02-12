# Copyright (c) 2010-2015 OpenStack Foundation
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

import unittest
from unittest import mock

import docker.client
import docker.errors
import docker.models.containers

from storlets.sbus.client import SBusResponse
from storlets.sbus.client.exceptions import SBusClientIOError, \
    SBusClientMalformedResponse, SBusClientSendError
from storlets.gateway.common.exceptions import StorletRuntimeException, \
    StorletTimeout
from storlets.gateway.gateways.docker.runtime import DockerRunTimeSandbox
from tests.unit import FakeLogger


class TestDockerRunTimeSandbox(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        # TODO(takashi): take these values from config file
        self.conf = {'container_image_namespace': 'localhost:5001',
                     'default_container_image_name': 'defaultimage'}
        self.scope = '0123456789abc'
        self.sbox = DockerRunTimeSandbox(self.scope, self.conf, self.logger)

    def test_ping(self):
        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'SBusClient.ping') as ping:
            ping.return_value = SBusResponse(True, 'OK')
            self.assertTrue(self.sbox.ping())

        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'SBusClient.ping') as ping:
            ping.return_value = SBusResponse(False, 'Error')
            self.assertFalse(self.sbox.ping())

        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'SBusClient.ping') as ping:
            ping.side_effect = SBusClientSendError()
            self.assertFalse(self.sbox.ping())

        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'SBusClient.ping') as ping:
            ping.side_effect = SBusClientMalformedResponse()
            self.assertFalse(self.sbox.ping())

        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'SBusClient.ping') as ping:
            ping.side_effect = SBusClientIOError()
            self.assertFalse(self.sbox.ping())

    def test_wait(self):
        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'SBusClient.ping') as ping, \
                mock.patch('storlets.gateway.gateways.container.runtime.'
                           'time.sleep') as sleep:
            ping.return_value = SBusResponse(True, 'OK')
            self.sbox.wait()
            self.assertEqual(sleep.call_count, 0)

        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'SBusClient.ping') as ping, \
            mock.patch('storlets.gateway.gateways.container.runtime.'
                       'time.sleep') as sleep:
            ping.side_effect = [SBusResponse(False, 'Error'),
                                SBusResponse(True, 'OK')]
            self.sbox.wait()
            self.assertEqual(sleep.call_count, 1)

        # TODO(takashi): should test timeout case

    def test__restart(self):
        # storlet container is not running
        with mock.patch('storlets.gateway.gateways.docker.runtime.'
                        'docker.from_env') as docker_from_env:
            mock_client = mock.MagicMock(spec_set=docker.client.DockerClient)
            mock_containers = mock.MagicMock(
                spec_set=docker.models.containers.ContainerCollection)
            mock_client.containers = mock_containers
            mock_containers.get.side_effect = \
                docker.errors.NotFound('container is not found')
            docker_from_env.return_value = mock_client

            self.sbox._restart('storlet_image')
            self.assertEqual(1, mock_containers.get.call_count)
            self.assertEqual(0, mock_containers.list.call_count)
            self.assertEqual(1, mock_containers.run.call_count)

        # storlet container is running
        with mock.patch('storlets.gateway.gateways.docker.runtime.'
                        'docker.from_env') as docker_from_env:
            mock_client = mock.MagicMock(spec_set=docker.client.DockerClient)
            mock_containers = mock.MagicMock(
                spec_set=docker.models.containers.ContainerCollection)
            mock_client.containers = mock_containers
            mock_container = \
                mock.MagicMock(spec_set=docker.models.containers.Container)
            mock_containers.get.return_value = mock_container
            docker_from_env.return_value = mock_client

            self.sbox._restart('storlet_image')
            self.assertEqual(1, mock_containers.get.call_count)
            self.assertEqual(1, mock_container.stop.call_count)
            self.assertEqual(0, mock_containers.list.call_count)
            self.assertEqual(1, mock_containers.run.call_count)

        # get failed
        with mock.patch('storlets.gateway.gateways.docker.runtime.'
                        'docker.from_env') as docker_from_env:
            mock_client = mock.MagicMock(spec_set=docker.client.DockerClient)
            mock_containers = mock.MagicMock(
                spec_set=docker.models.containers.ContainerCollection)
            mock_client.containers = mock_containers
            mock_containers.get.side_effect = \
                docker.errors.APIError('api error')
            docker_from_env.return_value = mock_client

            with self.assertRaises(StorletRuntimeException):
                self.sbox._restart('storlet_image')
            self.assertEqual(1, mock_containers.get.call_count)
            self.assertEqual(0, mock_containers.run.call_count)

        # stop failed
        with mock.patch('storlets.gateway.gateways.docker.runtime.'
                        'docker.from_env') as docker_from_env:
            mock_client = mock.MagicMock(spec_set=docker.client.DockerClient)
            mock_containers = mock.MagicMock(
                spec_set=docker.models.containers.ContainerCollection)
            mock_client.containers = mock_containers
            mock_container = \
                mock.MagicMock(spec_set=docker.models.containers.Container)
            mock_containers.get.return_value = mock_container
            mock_container.stop.side_effect = \
                docker.errors.APIError('api error')
            docker_from_env.return_value = mock_client

            with self.assertRaises(StorletRuntimeException):
                self.sbox._restart('storlet_image')
            self.assertEqual(1, mock_containers.get.call_count)
            self.assertEqual(1, mock_container.stop.call_count)
            self.assertEqual(0, mock_containers.list.call_count)
            self.assertEqual(0, mock_containers.run.call_count)

        # run failed
        with mock.patch('storlets.gateway.gateways.docker.runtime.'
                        'docker.from_env') as docker_from_env:
            mock_client = mock.MagicMock(spec_set=docker.client.DockerClient)
            mock_containers = mock.MagicMock(
                spec_set=docker.models.containers.ContainerCollection)
            mock_containers.run.side_effect = \
                docker.errors.APIError('api error')
            mock_client.containers = mock_containers
            mock_container = \
                mock.MagicMock(spec_set=docker.models.containers.Container)
            mock_containers.get.return_value = mock_container
            docker_from_env.return_value = mock_client

            with self.assertRaises(StorletRuntimeException):
                self.sbox._restart('storlet_image')
            self.assertEqual(1, mock_containers.get.call_count)
            self.assertEqual(1, mock_container.stop.call_count)
            self.assertEqual(0, mock_containers.list.call_count)
            self.assertEqual(1, mock_containers.run.call_count)

        # Set the limit
        self.sbox.max_containers_per_node = 2

        with mock.patch('storlets.gateway.gateways.docker.runtime.'
                        'docker.from_env') as docker_from_env:
            mock_client = mock.MagicMock(spec_set=docker.client.DockerClient)
            mock_containers = mock.MagicMock(
                spec_set=docker.models.containers.ContainerCollection)
            mock_client.containers = mock_containers
            mock_container = \
                mock.MagicMock(spec_set=docker.models.containers.Container)
            mock_containers.get.return_value = mock_container
            mock_containers.list.return_value = [mock.MagicMock()]
            docker_from_env.return_value = mock_client

            self.sbox._restart('storlet_image')
            self.assertEqual(1, mock_containers.get.call_count)
            self.assertEqual(1, mock_container.stop.call_count)
            self.assertEqual(1, mock_containers.list.call_count)
            self.assertEqual(1, mock_containers.run.call_count)

        with mock.patch('storlets.gateway.gateways.docker.runtime.'
                        'docker.from_env') as docker_from_env:
            mock_client = mock.MagicMock(spec_set=docker.client.DockerClient)
            mock_containers = mock.MagicMock(
                spec_set=docker.models.containers.ContainerCollection)
            mock_client.containers = mock_containers
            mock_container = \
                mock.MagicMock(spec_set=docker.models.containers.Container)
            mock_containers.get.return_value = mock_container
            mock_containers.list.return_value = [mock.MagicMock()] * 2
            docker_from_env.return_value = mock_client

            with self.assertRaises(StorletRuntimeException):
                self.sbox._restart('storlet_image')
            self.assertEqual(1, mock_containers.get.call_count)
            self.assertEqual(1, mock_container.stop.call_count)
            self.assertEqual(1, mock_containers.list.call_count)
            self.assertEqual(0, mock_containers.run.call_count)

    def test_restart(self):
        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'RunTimePaths.create_host_pipe_dir') as pipe_dir, \
                mock.patch('storlets.gateway.gateways.docker.runtime.'
                           'DockerRunTimeSandbox._restart') as _restart, \
                mock.patch('storlets.gateway.gateways.docker.runtime.'
                           'DockerRunTimeSandbox.wait') as wait:
            self.sbox.restart()
            self.assertEqual(1, pipe_dir.call_count)
            self.assertEqual(1, _restart.call_count)
            self.assertEqual((self.scope,), _restart.call_args.args)
            self.assertEqual(1, wait.call_count)

        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'RunTimePaths.create_host_pipe_dir') as pipe_dir, \
                mock.patch('storlets.gateway.gateways.docker.runtime.'
                           'DockerRunTimeSandbox._restart') as _restart, \
                mock.patch('storlets.gateway.gateways.docker.runtime.'
                           'DockerRunTimeSandbox.wait') as wait:
            _restart.side_effect = [StorletRuntimeException(), None]
            self.sbox.restart()
            self.assertEqual(1, pipe_dir.call_count)
            self.assertEqual(2, _restart.call_count)
            self.assertEqual((self.scope,),
                             _restart.call_args_list[0].args)
            self.assertEqual(('defaultimage',),
                             _restart.call_args_list[1].args)
            self.assertEqual(1, wait.call_count)

        with mock.patch('storlets.gateway.gateways.container.runtime.'
                        'RunTimePaths.create_host_pipe_dir') as pipe_dir, \
                mock.patch('storlets.gateway.gateways.docker.runtime.'
                           'DockerRunTimeSandbox._restart') as _restart, \
                mock.patch('storlets.gateway.gateways.docker.runtime.'
                           'DockerRunTimeSandbox.wait') as wait:
            _restart.side_effect = StorletTimeout()
            with self.assertRaises(StorletRuntimeException):
                self.sbox.restart()
            self.assertEqual(1, pipe_dir.call_count)
            self.assertEqual(1, _restart.call_count)
            self.assertEqual((self.scope,), _restart.call_args.args)
            self.assertEqual(0, wait.call_count)

    def test_get_storlet_classpath(self):
        storlet_id = 'Storlet.jar'
        storlet_main = 'org.openstack.storlet.Storlet'
        dependencies = ['dep1', 'dep2']
        self.assertEqual(
            '/home/swift/org.openstack.storlet.Storlet/Storlet.jar:'
            '/home/swift/org.openstack.storlet.Storlet/dep1:'
            '/home/swift/org.openstack.storlet.Storlet/dep2',
            self.sbox._get_storlet_classpath(storlet_main, storlet_id,
                                             dependencies),)


if __name__ == '__main__':
    unittest.main()
