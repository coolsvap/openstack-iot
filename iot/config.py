"""IOT specific config handling."""

#from oslo.config import cfg
#from iot import version
from magnum.api import hooks


# Server Specific Configurations
server = {
    'port': '8080',
    'host': '10.77.206.83'
}

# Pecan Application Configurations
app = {
    'root': 'iot.api.controllers.root.RootController',
    'modules': ['iot.api'],
    'debug': True,
    'hooks': [
        hooks.ContextHook(),
        hooks.RPCHook(),
        #hooks.NoExceptionTracebackHook(),
    ],
    'acl_public_routes': [
        '/'
    ],
 
}
