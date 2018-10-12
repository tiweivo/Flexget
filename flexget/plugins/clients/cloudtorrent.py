from __future__ import unicode_literals, division, absolute_import
from builtins import *  # noqa pylint: disable=unused-import, redefined-builtin

import logging
from socket import error as socket_error

from flexget import plugin
from flexget.event import event
from flexget.utils import requests

log = logging.getLogger('cloudtorrent')


class OutputCloudTorrent(object):
    """
    Simple CloudTorrent[https://github.com] output 

    Example::

        cloudtorrent:
          server: localhost
          port: 3000
          username: username
          password: password

    """

    schema = {
        'type': 'object',
        'properties': {
            'server': {'type': 'string', 'default': 'localhost'},
            'port': {'type': 'integer', 'default': 3000},
            'username': {'type': 'string', 'default': ''},
            'password': {'type': 'string', 'default': ''}

        },
        'required': [],
        'additionalProperties': False
    }

    def cloudtorrent_connection(self, server, port, username=None, password=None):
        if username and password:
            userpass = '%s:%s@' % (username, password)
        else:
            userpass = ''
        url = 'http://%s%s:%s' % (userpass, server, port)
        log.debug('cloudtorrent url: %s' % url)
        log.info('Connecting to cloudtorrent at %s', url)
        session = requests.Session()
        session.url = url
        return session

    def prepare_config(self, config):
        config.setdefault('server', 'localhost')
        config.setdefault('port', 3000)
        config.setdefault('username', '')
        config.setdefault('password', '')
        return config

    def on_task_output(self, task, config):
        # don't add when learning
        if task.options.learn:
            return
        config = self.prepare_config(config)
        cloudtorrent = self.cloudtorrent_connection(config['server'], config['port'],
                                      config['username'], config['password'])
        for entry in task.accepted:
            if task.options.test:
                log.verbose('Would add `%s` to cloudtorrent.', entry['title'])
                continue
            try:
                resp = self.add_entry(cloudtorrent, entry)
                log.info('Sent %s to cloud-torrent, server response: %s' % (entry['url'], resp.text))
            except socket_error as se:
                entry.fail('Unable to reach CloudTorrent: %s' % se)
            except Exception as e:
                log.debug('Exception type %s', type(e), exc_info=True)
                raise

    def add_entry(self, cloudtorrent, entry):
        """
        Add entry to CloudTorrent
        """
        return cloudtorrent.post(cloudtorrent.url + '/api/magnet', entry['url'])



@event('plugin.register')
def register_plugin():
    plugin.register(OutputCloudTorrent, 'cloudtorrent', api_ver=2)
