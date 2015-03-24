#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""API for interfacing with IoT Backend."""
from oslo.config import cfg

from iot.common import rpc_service
from iot import objects


# The Backend API class serves as a AMQP client for communicating
# on a topic exchange specific to the conductors.  This allows the ReST
# API to trigger operations on the conductors

class API(rpc_service.API):
    def __init__(self, transport=None, context=None, topic=None):
        if topic is None:
            cfg.CONF.import_opt('topic', 'iot.conductor.config',
                                group='conductor')
        super(API, self).__init__(transport, context,
                                  topic=cfg.CONF.conductor.topic)

    # Device operations

    def device_create(self, name, device_uuid, device):
        return self._call('device_create', name=name,
                          device_uuid=device_uuid,
                          device=device)

    def device_list(self, context, limit, marker, sort_key, sort_dir):
        return objects.Device.list(context, limit, marker, sort_key,
                                      sort_dir)

    def device_delete(self, device_uuid):
        return self._call('device_delete', device_uuid=device_uuid)

    def device_show(self, device_uuid):
        return self._call('device_show', device_uuid=device_uuid)
