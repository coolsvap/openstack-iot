#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from iot.common import exception
from iot.common import utils
from iot.db import api as dbapi
from iot.objects import base
from iot.objects import utils as obj_utils


class Device(base.IoTObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'project_id': obj_utils.str_or_none,
        'user_id': obj_utils.str_or_none,
        'image_id': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(device, db_device):
        """Converts a database entity to a formal object."""
        for field in device.fields:
            device[field] = db_device[field]

        device.obj_reset_changes()
        return device

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Device._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get(cls, context, device_id):
        """Find a device based on its id or uuid and return a Device object.

        :param device_id: the id *or* uuid of a device.
        :returns: a :class:`Device` object.
        """
        if utils.is_int_like(device_id):
            return cls.get_by_id(context, device_id)
        elif utils.is_uuid_like(device_id):
            return cls.get_by_uuid(context, device_id)
        else:
            raise exception.InvalidIdentity(identity=device_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, device_id):
        """Find a device based on its integer id and return a Device object.

        :param device_id: the id of a device.
        :returns: a :class:`Device` object.
        """
        db_device = cls.dbapi.get_device_by_id(device_id)
        device = Device._from_db_object(cls(context), db_device)
        return device

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a device based on uuid and return a :class:`Device` object.

        :param uuid: the uuid of a device.
        :param context: Security context
        :returns: a :class:`Device` object.
        """
        db_device = cls.dbapi.get_device_by_uuid(uuid)
        device = Device._from_db_object(cls(context), db_device)
        return device

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of Device objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Device` object.

        """
        db_devices = cls.dbapi.get_device_list(limit=limit,
                                         marker=marker,
                                         sort_key=sort_key,
                                         sort_dir=sort_dir)
        return Device._from_db_object_list(db_devices, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a Device record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Device(context)

        """
        values = self.obj_get_changes()
        db_device = self.dbapi.create_device(values)
        self._from_db_object(self, db_device)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Device from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Device(context)
        """
        self.dbapi.destroy_device(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Device.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Device(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_device(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this Device.

        Loads a device with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded device column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Device(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]
