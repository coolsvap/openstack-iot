#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""IoT base exception handling.

Includes decorator for re-raising IoT-type exceptions.

"""

import functools
import sys
import uuid

from keystoneclient import exceptions as keystone_exceptions
from oslo.config import cfg
from oslo.utils import excutils
import pecan
import six
import wsme

from iot.common import safe_utils
from iot.openstack.common._i18n import _
from iot.openstack.common._i18n import _LE
from iot.openstack.common import log as logging


LOG = logging.getLogger(__name__)

exc_log_opts = [
    cfg.BoolOpt('fatal_exception_format_errors',
                default=False,
                help='make exception message format errors fatal')
]

CONF = cfg.CONF
CONF.register_opts(exc_log_opts)


def wrap_exception(notifier=None, publisher_id=None, event_type=None,
                   level=None):
    """This decorator wraps a method to catch any exceptions.

    It logs the exception as well as optionally sending
    it to the notification system.
    """
    def inner(f):
        def wrapped(self, context, *args, **kw):
            # Don't store self or context in the payload, it now seems to
            # contain confidential information.
            try:
                return f(self, context, *args, **kw)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    if notifier:
                        call_dict = safe_utils.getcallargs(f, *args, **kw)
                        payload = dict(exception=e,
                                       private=dict(args=call_dict)
                                       )

                        # Use a temp vars so we don't shadow
                        # our outer definitions.
                        temp_level = level
                        if not temp_level:
                            temp_level = notifier.ERROR

                        temp_type = event_type
                        if not temp_type:
                            # If f has multiple decorators, they must use
                            # functools.wraps to ensure the name is
                            # propagated.
                            temp_type = f.__name__

                        notifier.notify(context, publisher_id, temp_type,
                                        temp_level, payload)

        return functools.wraps(f)(wrapped)
    return inner


OBFUSCATED_MSG = _('Your request could not be handled '
                   'because of a problem in the server. '
                   'Error Correlation id is: %s')


def wrap_controller_exception(func, func_server_error, func_client_error):
    """This decorator wraps controllers methods to handle exceptions:

    - if an unhandled Exception or a IoTException with an error code >=500
    is catched, raise a http 5xx ClientSideError and correlates it with a log
    message

    - if a IoTException is catched and its error code is <500, raise a http
    4xx and logs the excp in debug mode

    """
    @functools.wraps(func)
    def wrapped(*args, **kw):
        try:
            return func(*args, **kw)
        except Exception as excp:
            if isinstance(excp, IoTException):
                http_error_code = excp.code
            else:
                http_error_code = 500

            if http_error_code >= 500:
                # log the error message with its associated
                # correlation id
                log_correlation_id = str(uuid.uuid4())
                LOG.error("%s:%s", log_correlation_id, str(excp))
                # raise a client error with an obfuscated message
                func_server_error(log_correlation_id, http_error_code)
            else:
                # raise a client error the original message
                LOG.debug(excp)
                func_client_error(excp, http_error_code)
    return wrapped


def wrap_wsme_controller_exception(func):
    """This decorator wraps wsme controllers to handle exceptions."""
    def _func_server_error(log_correlation_id, status_code):
        raise wsme.exc.ClientSideError(
            six.text_type(OBFUSCATED_MSG % log_correlation_id), status_code)

    def _func_client_error(excp, status_code):
        raise wsme.exc.ClientSideError(six.text_type(excp), status_code)

    return wrap_controller_exception(func,
                                     _func_server_error,
                                     _func_client_error)


def wrap_pecan_controller_exception(func):
    """This decorator wraps pecan controllers to handle exceptions."""
    def _func_server_error(log_correlation_id, status_code):
        pecan.response.status = status_code
        pecan.response.text = six.text_type(OBFUSCATED_MSG %
                                            log_correlation_id)

    def _func_client_error(excp, status_code):
        pecan.response.status = status_code
        pecan.response.text = six.text_type(excp)
        pecan.response.content_type = None

    return wrap_controller_exception(func,
                                     _func_server_error,
                                     _func_client_error)


def wrap_keystone_exception(func):
    """Wrap keystone exceptions and throw IoT specific exceptions."""
    @functools.wraps(func)
    def wrapped(*args, **kw):
        try:
            return func(*args, **kw)
        except keystone_exceptions.AuthorizationFailure:
            raise AuthorizationFailure(
                client=func.__name__, message="reason: %s" % sys.exc_info()[1])
        except keystone_exceptions.ClientException:
            raise AuthorizationFailure(
                client=func.__name__,
                message="unexpected keystone client error occurred: %s"
                        % sys.exc_info()[1])
    return wrapped


class IoTException(Exception):
    """Base IoT Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")
    code = 500

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                self.message = self.message % kwargs

            except Exception as e:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_LE('Exception in string format operation'))
                for name, value in kwargs.iteritems():
                    LOG.error("%s: %s" % (name, value))

                if CONF.fatal_exception_format_errors:
                    raise e
                else:
                    # at least get the core message out if something happened
                    message = self.message

        super(IoTException, self).__init__(self.message)

    def __str__(self):
        if six.PY3:
            return self.message
        return self.message.encode('utf-8')

    def __unicode__(self):
        return self.message

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return six.text_type(self)


class ObjectNotFound(IoTException):
    message = _("The %(name)s %(id)s could not be found.")


class ObjectNotUnique(IoTException):
    message = _("The %(name)s already exists.")


class ResourceNotFound(ObjectNotFound):
    message = _("The %(name)s resource %(id)s could not be found.")
    code = 404


class ResourceExists(ObjectNotUnique):
    message = _("The %(name)s resource already exists.")
    code = 409


class AuthorizationFailure(IoTException):
    message = _("%(client)s connection failed. %(message)s")


class UnsupportedObjectError(IoTException):
    message = _('Unsupported object type %(objtype)s')


class IncompatibleObjectVersion(IoTException):
    message = _('Version %(objver)s of %(objname)s is not supported')


class OrphanedObjectError(IoTException):
    message = _('Cannot call %(method)s on orphaned %(objtype)s object')


class Invalid(IoTException):
    message = _("Unacceptable parameters.")
    code = 400


class InvalidUUID(Invalid):
    message = _("Expected a uuid but received %(uuid)s.")


class InvalidIdentity(Invalid):
    message = _("Expected an uuid or int but received %(identity)s.")


class HTTPNotFound(ResourceNotFound):
    pass


class Conflict(IoTException):
    message = _('Conflict.')
    code = 409


class InvalidState(Conflict):
    message = _("Invalid resource state.")


# Cannot be templated as the error syntax varies.
# msg needs to be constructed when raised.
class InvalidParameterValue(Invalid):
    message = _("%(err)s")


class InstanceAssociated(Conflict):
    message = _("Instance %(instance_uuid)s is already associated with a node,"
                " it cannot be associated with this other node %(node)s")


class InstanceNotFound(ResourceNotFound):
    message = _("Instance %(instance)s could not be found.")


class PatchError(Invalid):
    message = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


class NotAuthorized(IoTException):
    message = _("Not authorized.")
    code = 403


class OperationNotPermitted(NotAuthorized):
    message = _("Operation not permitted.")


class InvalidMAC(Invalid):
    message = _("Expected a MAC address but received %(mac)s.")


class ConfigInvalid(IoTException):
    message = _("Invalid configuration file. %(error_msg)s")



class SSHConnectFailed(IoTException):
    message = _("Failed to establish SSH connection to host %(host)s.")


class FileSystemNotSupported(IoTException):
    message = _("Failed to create a file system. "
                "File system %(fs)s is not supported.")

class DeviceNotFound(ResourceNotFound):
    message = _("Device %(device)s could not be found.")


class DeviceAlreadyExists(Conflict):
    message = _("A device with UUID %(uuid)s already exists.")


class KeystoneUnauthorized(IoTException):
    message = _("Not authorized in Keystone.")


class KeystoneFailure(IoTException):
    message = _("Keystone failed.")


class CatalogNotFound(IoTException):
    message = _("Service type %(service_type)s with endpoint type "
                "%(endpoint_type)s not found in keystone service catalog.")
