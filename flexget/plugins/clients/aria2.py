from __future__ import unicode_literals, division, absolute_import
from builtins import *  # pylint: disable=unused-import, redefined-builtin

import logging
import re
import os
import xmlrpc.client

from flexget import plugin
from flexget.event import event
from flexget.utils.template import RenderError

from socket import error as socket_error

log = logging.getLogger('aria2')


class OutputAria2(object):
    """
    Simple Aria2 output

    Example::

        aria2:
          path: ~/downloads/

    """

    schema = {
        'type': 'object',
        'properties': {
            'server': {'type': 'string', 'default': 'localhost'},
            'port': {'type': 'integer', 'default': 6800},
            'secret': {'type': 'string', 'default': ''},
            'username': {'type': 'string', 'default': ''}, # NOTE: To be deprecated by aria2
            'password': {'type': 'string', 'default': ''},
            'path': {'type': 'string', 'format': 'path'},
            'options': {
                'type': 'object',
                'additionalProperties': {'oneOf': [{'type': 'string'}, {'type': 'integer'}]}
            }

        },
        'required': ['path'],
        'additionalProperties': False
    }

    def aria2_connection(self, server, port, username=None, password=None):
        try:
            if username and password:
                userpass = '%s:%s@' % (username, password)
            else:
                userpass = ''
            url = 'http://%s%s:%s/rpc' % (userpass, server, port)
            log.debug('aria2 url: %s' % url)
            log.info('Connected to daemon at %s', url)
            return xmlrpc.client.ServerProxy(url).aria2
        except xmlrpc.client.ProtocolError as err:
            raise plugin.PluginError('Could not connect to aria2 at %s. Protocol error %s: %s'
                              % (url, err.errcode, err.errmsg), log)
        except xmlrpc.client.Fault as err:
            raise plugin.PluginError('XML-RPC fault: Unable to connect to aria2 daemon at %s: %s'
                              % (url, err.faultString), log)
        except socket_error as e:
            _, msg = e.args
            raise plugin.PluginError('Socket connection issue with aria2 daemon at %s: %s' % (url, msg), log)
        except:
            log.debug('Unexpected error during aria2 connection', exc_info=True)
            raise plugin.PluginError('Unidentified error during connection to aria2 daemon', log)

    def prepare_config(self, config):
        config.setdefault('server', 'localhost')
        config.setdefault('port', 6800)
        config.setdefault('username', '')
        config.setdefault('password', '')
        config.setdefault('secret', '')
        config.setdefault('options', {})
        return config

    def on_task_output(self, task, config):
        # don't add when learning
        if task.options.learn:
            return
        config = self.prepare_config(config)
        aria2 = self.aria2_connection(config['server'], config['port'],
                                      config['username'], config['password'])
        for entry in task.accepted:
            try:
                self.add_entry(aria2, entry, config)
            except socket_error as se:
                entry.fail('Unable to reach Aria2')

    def add_entry(self, aria2, entry, config):
        """
        Add entry to Aria2
        """
        options = config['options']
        options['dir'] = os.path.expanduser(entry.render(config['path']).rstrip('/'))
        # handle torrent files
        if 'torrent' in entry:
            return aria2.addTorrent(xmlrpclib.Binary(open(entry['file'], mode='rb').read()))
        # handle everything else (except metalink -- which is unsupported)
        # so magnets, https, http, ftp .. etc
        if config['secret']:
            return aria2.addUri(config['secret'], [entry['url']], options)
        return aria2.addUri([entry['url']], options)


@event('plugin.register')
def register_plugin():
    plugin.register(OutputAria2, 'aria2', api_ver=2)
