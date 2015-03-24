# Copyright 2013 UnitedStack Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
import uuid
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from iot.api.controllers import base
from iot.api.controllers import link
from iot.api.controllers.v1 import collection
from iot.api.controllers.v1 import types
from iot.api.controllers.v1 import utils as api_utils
from iot.common import context
from iot.common import exception
from iot import objects
from iot.openstack.common import log as logging

#from iot.api.controllers.v1.base import _Base 
#from iot.api.controllers.v1.base import Query 

LOG = logging.getLogger(__name__)


class DevicePatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/device_uuid']


class Device(base.APIBase):
    """API representation of a device.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    device.
    """

    uuid = wtypes.text
    """Unique UUID for this device"""

    name = wtypes.text
    """Name of this device"""

    desc = wtypes.text
    """Device Description."""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated iot links"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in Objects.Device.fields:
            if not hasattr(self, fields):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wstypes.Unset))

    @staticmethod
    def convert_with_links(device, url, expand=True):
        if not expand:
            device.unset_fields_except(['uuid', 'name', 'desc'])

        device.links = [link.Link.make_link('self', url,
                                            'devices', device.uuid),
                        link.Link.make_link('bookmark', url,
                                            'devices', device.uuid,
                                            bookmark=True)
                        ]
        return device

    @classmethod
    def covert_with_links(cls, rpc_device, expand=True):
        device = Device(**rpc_device.as_dict())
        return cls._convert_with_links(device, pecan.request.host_url,
                                       expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid=str(uuid.uuid1()),
                    name='example',
                    desc="IOT Device",
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow())
        sample._device_uuid = str(uuid.uuid1())
        return cls._convert_with_links(sample, 'http://localhost:9513', expand)


class DeviceCollection(collection.Collection):
    """API representation of a collection of devices."""

    devices = [Device]
    """A list containing device objects"""

    def __init__(self, **kwargs):
        self._type = 'devices'

    @staticmethod
    def convert_with_links(rpc_devices, limit, url=None,
                           expand=False, **kwargs):
        collection = DeviceCollection()
        collection.devices = [Devices.convert_with_links(p, expand)
                            for p in rpc_devices]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.devices= [Device.sample(expand=False)]
        return sample


class DevicesController(rest.RestController):
    """REST controller for Devices."""
    
    def __init__(self):
        super(DevicesController, self).__init__()

    from_devices = False
    """A flag to indicate if the requests to this device are coming
    from the top-level resource Devices."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_devices_collection(self, marker, limit,
                              sort_key, sort_dir, expand=False,
                              resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Device.get_by_uuid(pecan.request.context,
                                                  marker)

        devices = objects.Device.list(pecan.request.context, limit,
                                            marker_obj, sort_key=sort_key,
                                            sort_dir=sort_dir)

        return DeviceCollection.convert_with_links(devices, limit,
                                                url=resource_url,
                                                expand=expand,
                                                sort_key=sort_key,
                                                sort_dir=sort_dir)

    #@wsme_pecan.wsexpose([Device], [Query], int)
    @wsme_pecan.wsexpose(DeviceCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, device_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve definitions of all of the devices."""
    
        return self._get_devices_collection(marker, limit, sort_key,
                                        sort_dir)
        #return [Device.sample(), Device.sample()]


    @wsme_pecan.wsexpose(DeviceCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def detail(self, device_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of devices with detail."""

        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "devices":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['devices', 'detail'])
        return self._get_devices_collection(marker, limit,
                                         sort_key, sort_dir, expand,
                                         resource_url)

    @wsme_pecan.wsexpose(Device, wtypes.text)
    def get_one(self, device_uuid): 
        """Retrieve information about given device."""

        if self.from_devices:
            raise exception.OperationNotPermitted()

        rpc_device = objects.Device.get_by_uuid(pecan.request.context,
                                                device_uuid)
        return Device.converts_with_links(rpc_device)
        #return Device.sample()
