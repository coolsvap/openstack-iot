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

"""SQLAlchemy storage backend."""

from oslo.config import cfg
from oslo.db import exception as db_exc
from oslo.db.sqlalchemy import session as db_session
from oslo.db.sqlalchemy import utils as db_utils
from oslo.utils import timeutils
from sqlalchemy.orm.exc import NoResultFound

from iot.common import exception
from iot.common import utils
from iot.db import api
from iot.db.sqlalchemy import models
from iot.openstack.common._i18n import _
from iot.openstack.common import log

CONF = cfg.CONF

LOG = log.getLogger(__name__)


_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def get_backend():
    """The backend is this module itself."""
    return Connection()


def model_query(model, *args, **kwargs):
    """Query helper for simpler session usage.

    :param session: if present, the session to use
    """

    session = kwargs.get('session') or get_session()
    query = session.query(model, *args)
    return query


def add_identity_filter(query, value):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if utils.is_int_like(value):
        return query.filter_by(id=value)
    elif utils.is_uuid_like(value):
        return query.filter_by(uuid=value)
    else:
        raise exception.InvalidIdentity(identity=value)


def _paginate_query(model, limit=None, marker=None, sort_key=None,
                    sort_dir=None, query=None):
    if not query:
        query = model_query(model)
    sort_keys = ['id']
    if sort_key and sort_key not in sort_keys:
        sort_keys.insert(0, sort_key)
    query = db_utils.paginate_query(query, model, limit, sort_keys,
                                    marker=marker, sort_dir=sort_dir)
    return query.all()


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_devices_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'name' in filters:
            query = query.filter_by(name=filters['name'])
        if 'image_id' in filters:
            query = query.filter_by(image_id=filters['image_id'])

        return query

    def get_deviceinfo_list(self, columns=None, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        # list-ify columns default values because it is bad form
        # to include a mutable list in function definitions.
        if columns is None:
            columns = [models.Device.id]
        else:
            columns = [getattr(models.Device, c) for c in columns]

        query = model_query(*columns, base_model=models.Device)
        query = self._add_devices_filters(query, filters)
        return _paginate_query(models.Device, limit, marker,
                               sort_key, sort_dir, query)

    def get_device_list(self, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None):
        query = model_query(models.Device)
        query = self._add_devices_filters(query, filters)
        return _paginate_query(models.Device, limit, marker,
                               sort_key, sort_dir, query)

    def create_device(self, values):
        # ensure defaults are present for new devices
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        device = models.Device()
        device.update(values)
        try:
            device.save()
        except db_exc.DBDuplicateEntry:
            raise exception.DeviceAlreadyExists(uuid=values['uuid'])
        return device

    def get_device_by_id(self, device_id):
        query = model_query(models.Device).filter_by(id=device_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.DeviceNotFound(device=device_id)

    def get_device_by_uuid(self, device_uuid):
        query = model_query(models.Device).filter_by(uuid=device_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.DeviceNotFound(device=device_uuid)

    def destroy_device(self, device_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Device, session=session)
            query = add_identity_filter(query, device_id)
            count = query.delete()
            if count != 1:
                raise exception.DeviceNotFound(device_id)

    def update_device(self, device_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Device.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_device(device_id, values)

    def _do_update_device(self, device_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Device, session=session)
            query = add_identity_filter(query, device_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.DeviceNotFound(device=device_id)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref
