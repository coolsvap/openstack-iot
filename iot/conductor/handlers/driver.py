# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""IoT Docker RPC handler."""

from docker import errors
from oslo.config import cfg

from iot.common import docker_utils
from iot.openstack.common import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()
        self._docker = None

    def _encode_utf8(self, value):
        return unicode(value).encode('utf-8')

    # Device operations

    def device_create(self, ctxt, name, device_uuid, device):
        LOG.debug('Creating device name %s'
                  % (name))

    def device_list(self, ctxt):
        LOG.debug("device_list")

    def device_delete(self, ctxt, device_uuid):
        LOG.debug("device_delete %s" % device_uuid)

    def device_show(self, ctxt, device_uuid):
        LOG.debug("device_show %s" % device_uuid)
