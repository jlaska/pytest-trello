import os
import logging
import yaml
import pytest
import trello


"""
pytest-trello
~~~~~~~~~~~~

pytest-trello is a plugin for py.test that allows tests to reference trello
cards for skip/xfail handling.

:copyright: see LICENSE for details
:license: MIT, see LICENSE for more details.
"""


log = logging.getLogger(__name__)


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
                    # FIXME - change to Done after mocking
                    default=['Live (May 2014)'],
                    help='Any cards in TRELLO_COMPLETED are considered complete (default: %default)')


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

    # Verify a key and token were provided
    if not (config.option.help or config.option.collectonly or config.option.showfixtures):
        if os.path.isfile(trello_cfg_file):
            trello_cfg = yaml.load(open(trello_cfg_file, 'r'))
            # TODO - set the parser value here as well
            if trello_api_key is None:
                trello_api_key = trello_cfg.get('key', None)
            if trello_api_token is None:
                trello_api_token = trello_cfg.get('token', None)

        if False:
            if trello_api_key is None:  # or trello_api_key == '':
                msg = "ERROR: Missing required parameter --trello-api-key"
                print(msg)
                pytest.exit(msg)
            if trello_api_token is None:  # or trello_api_token == '':
                msg = "ERROR: Missing required parameter --trello-api-token"
                print(msg)
                pytest.exit(msg)

        api = trello.TrelloApi(trello_api_key, trello_api_token)

        # Create trello card cache
        config.trello_cache = dict()

        # Register pytest plugin
        assert config.pluginmanager.register(
            TrelloPytestPlugin(api, completed_lists=config.getvalue('trello_completed')),
            "trello_helper"
        )


class TrelloCard(object):
    def __init__(self, api, url, **kwargs):
        self.api = api
        self.url = url
        self._card = None
        self._board = None

    @property
    def hash(self):
        return os.path.basename(self.url)

    @property
    def card(self):
        if self._card is None:
            self._card = self.api.cards.get(self.hash)
        return self._card

    @property
    def name(self):
        return self.card['name']

    @property
    def board(self):
        if self._board is None:
            self._board = self.api.lists.get(self.card['idList'])['name']
        return self._board


class TrelloCardList(object):
    def __init__(self, api, *args, **kwargs):
        self.api = api
        self.cards = args
        self.xfail = kwargs.get('xfail', True) and not ('skip' in kwargs)

    def __iter__(self):
        for c in self.cards:
            yield c


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
            if card.board not in self.completed_lists:
                incomplete_cards.append(card)

        if incomplete_cards:
            if cards.xfail:
                item.add_marker(pytest.mark.xfail(
                    reason="Xfailing due to incomplete trello cards: \n{0}".format(
                        "\n ".join(["{0} [{1}] {2}".format(card.url, card.board, card.name) for card in incomplete_cards]))))
            else:
                pytest.skip("Skipping due to incomplete trello cards:\n{0}".format(
                    "\n ".join(["{0} [{1}] {2}".format(card.url, card.board, card.name) for card in incomplete_cards])))

    def pytest_collection_modifyitems(self, session, config, items):
        reporter = config.pluginmanager.getplugin("terminalreporter")
        reporter.write("collecting trello markers ", bold=True)
        for i, item in enumerate(filter(lambda i: i.get_marker("trello") is not None, items)):
            marker = item.get_marker('trello')
            cards = tuple(sorted(set(marker.args)))  # (O_O) for caching
            for card in cards:
                if card not in config.trello_cache:
                    reporter.write(".")
                    config.trello_cache[card] = TrelloCard(self.api, card)
            item.funcargs["cards"] = TrelloCardList(self.api, *[config.trello_cache[c] for c in cards], **marker.kwargs)
        reporter.write(" {0} collected\n".format(len(config.trello_cache)), bold=True)
