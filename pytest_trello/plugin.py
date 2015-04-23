import os
import logging
import yaml
import pytest
import trello
import requests.exceptions


"""
pytest-trello
~~~~~~~~~~~~

pytest-trello is a plugin for py.test that allows tests to reference trello
cards for skip/xfail handling.

:copyright: see LICENSE for details
:license: MIT, see LICENSE for more details.
"""


log = logging.getLogger(__name__)
_card_cache = {}
DEFAULT_TRELLO_COMPLETED = ['Done', 'Archived']


def pytest_addoption(parser):
    '''Add options to control trello integration.'''

    group = parser.getgroup('pytest-trello')
    group.addoption('--trello-cfg',
                    action='store',
                    dest='trello_cfg_file',
                    default='trello.yml',
                    metavar='TRELLO_CFG',
                    help='Trello configuration file (default: %default)')
    group.addoption('--trello-api-key',
                    action='store',
                    dest='trello_api_key',
                    default=None,
                    metavar='TRELLO_API_KEY',
                    help='Trello API key (defaults to value supplied in TRELLO_CFG)')
    group.addoption('--trello-api-token',
                    action='store',
                    dest='trello_api_token',
                    metavar='TRELLO_API_TOKEN',
                    default=None,
                    help='Trello API token (defaults to value supplied in TRELLO_CFG). Refer to https://trello.com/docs/gettingstarted/')
    group.addoption('--trello-completed',
                    action='append',
                    dest='trello_completed',
                    metavar='TRELLO_COMPLETED',
                    default=[],
                    help='Any cards in TRELLO_COMPLETED are considered complete (default: %s)' % DEFAULT_TRELLO_COMPLETED)


def pytest_configure(config):
    '''
    Validate --trello-* parameters.
    '''

    # Add marker
    config.addinivalue_line("markers", """trello(*cards): Trello card integration""")

    # Sanitize key and token
    trello_cfg_file = config.getoption('trello_cfg_file')
    trello_api_key = config.getoption('trello_api_key')
    trello_api_token = config.getoption('trello_api_token')
    trello_completed = config.getoption('trello_completed')

    # If not --help or --collectonly or --showfixtures ...
    if not (config.option.help or config.option.collectonly or config.option.showfixtures):
        # Warn if file does not exist
        if not os.path.isfile(trello_cfg_file):
            errstr = "No trello configuration file found matching: %s" % trello_cfg_file
            log.warning(errstr)

        # Load configuration file ...
        if os.path.isfile(trello_cfg_file):
            trello_cfg = yaml.load(open(trello_cfg_file, 'r'))
            try:
                trello_cfg = trello_cfg.get('trello', {})
            except AttributeError:
                trello_cfg = {}
                errstr = "No trello configuration found in file: %s" % trello_cfg_file
                log.warning(errstr)

            if trello_api_key is None:
                trello_api_key = trello_cfg.get('key', None)
            if trello_api_token is None:
                trello_api_token = trello_cfg.get('token', None)
            if trello_completed is None or trello_completed == []:
                trello_completed = trello_cfg.get('completed', [])

        # Initialize trello api connection
        api = trello.TrelloApi(trello_api_key, trello_api_token)

        # If completed is still empty, load default ...
        if trello_completed is None or trello_completed == []:
            trello_completed = DEFAULT_TRELLO_COMPLETED

        # Register pytest plugin
        assert config.pluginmanager.register(
            TrelloPytestPlugin(api, completed_lists=trello_completed),
            'trello_helper'
        )


class TrelloCard(object):
    '''Object representing a trello card.
    '''

    def __init__(self, api, url):
        self.api = api
        self.url = url
        self._card = None

    @property
    def id(self):
        return os.path.basename(self.url)

    @property
    def card(self):
        if self._card is None:
            try:
                self._card = self.api.cards.get(self.id)
            except ValueError, e:
                log.warning("Failed to retrieve card:%s - %s" % (self.id, e))
                pass
        return self._card

    @property
    def name(self):
        return self.card['name']

    @property
    def idList(self):
        return self.card['idList']

    @property
    def list(self):
        return TrelloList(self.api, self.idList)


class TrelloList(object):
    '''Object representing a trello list.
    '''

    def __init__(self, api, id):
        self.api = api
        self.id = id
        self._list = None

    @property
    def name(self):
        if self._list is None:
            try:
                self._list = self.api.lists.get(self.id)
            except ValueError, e:
                log.warning("Failed to retrieve list:%s - %s" % (self.id, e))
                pass
        return self._list['name']


class TrelloCardList(object):
    def __init__(self, api, *cards, **kwargs):
        self.api = api
        self.cards = cards
        self.xfail = kwargs.get('xfail', True) and not ('skip' in kwargs)

    def __iter__(self):
        for card in self.cards:
            if card not in _card_cache:
                _card_cache[card] = TrelloCard(self.api, card)
            yield _card_cache[card]


class TrelloPytestPlugin(object):
    def __init__(self, api, **kwargs):
        self.api = api
        self.completed_lists = kwargs.get('completed_lists', [])

    def pytest_runtest_setup(self, item):
        if 'trello' not in item.keywords:
            return

        incomplete_cards = []
        cards = item.funcargs["cards"]
        for card in cards:
            try:
                if card.list.name not in self.completed_lists:
                    incomplete_cards.append(card)
            except requests.exceptions.HTTPError, e:
                log.warning("Error accessing card:%s - %s" % (card.id, e))
                continue

        # item.get_marker('trello').kwargs
        if incomplete_cards:
            if cards.xfail:
                item.add_marker(pytest.mark.xfail(
                    reason="Xfailing due to incomplete trello cards: \n{0}".format(
                        "\n ".join(["{0} [{1}] {2}".format(card.url, card.list.name, card.name) for card in incomplete_cards]))))
            else:
                pytest.skip("Skipping due to incomplete trello cards:\n{0}".format(
                    "\n ".join(["{0} [{1}] {2}".format(card.url, card.list.name, card.name) for card in incomplete_cards])))

    def pytest_collection_modifyitems(self, session, config, items):
        reporter = config.pluginmanager.getplugin("terminalreporter")
        reporter.write("collected", bold=True)
        for i, item in enumerate(filter(lambda i: i.get_marker("trello") is not None, items)):
            marker = item.get_marker('trello')
            cards = tuple(sorted(set(marker.args)))  # (O_O) for caching
            for card in cards:
                if card not in _card_cache:
                    _card_cache[card] = TrelloCard(self.api, card)
            item.funcargs["cards"] = TrelloCardList(self.api, *cards, **marker.kwargs)
        reporter.write(" {0} trello markers\n".format(len(_card_cache)), bold=True)
