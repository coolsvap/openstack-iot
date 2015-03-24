#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
Base classes for storage engines
"""

import abc

from oslo.config import cfg
from oslo.db import api as db_api
import six


_BACKEND_MAPPING = {'sqlalchemy': 'iot.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF, backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class Connection(object):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def __init__(self):
        """Constructor."""

    @abc.abstractmethod
    def get_device_list(self, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching devices.

        Return a list of the specified columns for all devices that match
        the specified filters.

        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of devices to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_device(self, values):
        """Create a new device.

        :param values: A dict containing several items used to identify
                       and track the device, and several dicts which are
                       passed
                       into the Drivers when managing this device. For
                       example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
                         'name': 'example',
                         'type': 'virt'
                        }
        :returns: A device.
        """

    @abc.abstractmethod
    def get_device_by_id(self, device_id):
        """Return a device.

        :param device_id: The id of a device.
        :returns: A device.
        """

    @abc.abstractmethod
    def get_device_by_uuid(self, device_uuid):
        """Return a device.

        :param device_uuid: The uuid of a device.
        :returns: A device.
        """

    @abc.abstractmethod
    def destroy_device(self, device_id):
        """Destroy a device and all associated interfaces.

        :param device_id: The id or uuid of a device.
        """
