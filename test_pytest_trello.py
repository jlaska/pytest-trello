# -*- coding: utf-8 -*-
import pytest


pytest_plugins = 'pytester',

OPEN_CARDS = ['https://trello.com/c/open1234', 'https://trello.com/c/open4321']
CLOSED_CARDS = ['https://trello.com/c/closed12', 'https://trello.com/c/closed21']
ALL_CARDS = OPEN_CARDS + CLOSED_CARDS


def assert_outcome(result, passed=0, failed=0, skipped=0, xpassed=0, xfailed=0):
    '''This method works around a limitation where pytester assertoutcome()
    doesn't support xpassed and xfailed.
    '''

    actual_count = dict(passed=0, failed=0, skipped=0, xpassed=0, xfailed=0)

    reports = filter(lambda x: hasattr(x, 'when'), result.getreports())
    for report in reports:
        if report.when == 'setup':
            if report.skipped:
                actual_count['skipped'] += 1
        elif report.when == 'call':
            if hasattr(report, 'wasxfail'):
                if report.failed:
                    actual_count['xpassed'] += 1
                elif report.skipped:
                    actual_count['xfailed'] += 1
            else:
                actual_count[report.outcome] += 1
        else:
            continue

    assert passed == actual_count['passed']
    assert failed == actual_count['failed']
    assert skipped == actual_count['skipped']
    assert xfailed == actual_count['xfailed']
    assert xpassed == actual_count['xpassed']


class PyTestOption(object):

    def __init__(self, config=None):
        self.config = config

    @property
    def args(self):
        args = list()
        if self.config.getoption('trello_api_key') is not None:
            args.append('--trello-api-key')
            args.append(self.config.getoption('trello_api_key'))
        if self.config.getoption('trello_api_token') is not None:
            args.append('--trello-api-token')
            args.append(self.config.getoption('trello_api_token'))
        for completed in self.config.getoption('trello_completed'):
            args.append('--trello-completed')
            args.append('"%s"' % completed)
        return args


def mock_trello_card_get(self, card_id, **kwargs):
    '''Returns JSON representation of an trello card.'''
    if card_id.startswith("closed"):
        is_closed = True
    else:
        is_closed = False

    return {
        "labels": [],
        "pos": 33054719,
        "manualCoverAttachment": False,
        "badges": {},
        "id": "550c37c5226dd7241a61372f",
        "idBoard": "54aeece5d8b09a1947f34050",
        "idShort": 334,
        "shortUrl": "https://trello.com/c/%s" % card_id,
        "closed": False,
        "email": "nospam@boards.trello.com",
        "dateLastActivity": "2015-03-20T15:12:29.735Z",
        "idList": "%s53f20bbd90cfc68effae9544" % (is_closed and 'closed' or 'open'),
        "idLabels": [],
        "idMembers": [],
        "checkItemStates": [],
        "name": "mock trello card - %s" % (is_closed and 'closed' or 'open'),
        "desc": "mock trello card - %s" % (is_closed and 'closed' or 'open'),
        "descData": {},
        "url": "https://trello.com/c/%s" % card_id,
        "idAttachmentCover": None,
        "idChecklists": []
    }


def mock_trello_list_get(self, list_id, **kwargs):
    '''Returns JSON representation of a trello list containing open cards.'''
    if list_id.startswith("closed"):
        is_closed = True
    else:
        is_closed = False

    return {
        "pos": 124927.75,
        "idBoard": "54aeece5d8b09a1947f34050",
        "id": list_id,
        "closed": False,
        "name": is_closed and "Done" or "Not Done"
    }


@pytest.fixture()
def option(request):
    return PyTestOption(request.config)


@pytest.fixture()
def monkeypatch_trello(request, monkeypatch):
    monkeypatch.delattr("requests.get")
    monkeypatch.delattr("requests.sessions.Session.request")
    monkeypatch.setattr('trello.cards.Cards.get', mock_trello_card_get)
    monkeypatch.setattr('trello.lists.Lists.get', mock_trello_list_get)


def test_plugin_markers(testdir):
    '''Verifies expected output from of py.test --markers'''

    result = testdir.runpytest('--markers')
    result.stdout.fnmatch_lines([
        '@pytest.mark.trello(*cards): Trello card integration',
    ])


def test_plugin_help(testdir):
    '''Verifies expected output from of py.test --help'''

    result = testdir.runpytest('--help')
    result.stdout.fnmatch_lines([
        'pytest-trello:',
        '* --trello-cfg=TRELLO_CFG',
        '* --trello-api-key=TRELLO_API_KEY',
        '* --trello-api-token=TRELLO_API_TOKEN',
        '* --trello-completed=TRELLO_COMPLETED',
    ])


def test_pass_without_trello_card(testdir, option):
    '''Verifies test success when no trello card is supplied'''

    testdir.makepyfile("""
        import pytest
        def test_func():
            assert True
        """)
    result = testdir.runpytest(*option.args)
    assert result.ret == 0
    assert result.parseoutcomes()['passed'] == 1


def test_fail_without_trello_card(testdir, option):
    '''Verifies test failure when no trello card is supplied'''

    testdir.makepyfile("""
        import pytest
        def test_func():
            assert False
        """)
    result = testdir.runpytest(*option.args)
    assert result.ret == 1
    assert result.parseoutcomes()['failed'] == 1


def test_success_with_open_card(testdir, option, monkeypatch_trello):
    '''Verifies when a test succeeds with an open trello card'''

    src = """
        import pytest
        @pytest.mark.trello('%s')
        def test_func():
            assert True
        """ % OPEN_CARDS[0]
    # result = testdir.runpytest(*option.args)
    # assert result.ret == 0
    # assert result.parseoutcomes()['xpassed'] == 1
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, xpassed=1)


def test_success_with_open_cards(testdir, option, monkeypatch_trello):
    '''Verifies when a test succeeds with open trello cards'''

    src = """
        import pytest
        @pytest.mark.trello(*%s)
        def test_func():
            assert True
        """ % OPEN_CARDS
    # testdir.makepyfile(src)
    # result = testdir.runpytest(*option.args)
    # assert result.ret == 0
    # assert result.parseoutcomes()['xpassed'] == 1
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, xpassed=1)


def test_failure_with_open_card(testdir, option, monkeypatch_trello):
    '''Verifies when a test fails with an open trello card'''

    src = """
        import pytest
        @pytest.mark.trello('%s')
        def test_func():
            assert False
        """ % OPEN_CARDS[0]
    # testdir.makepyfile(src)
    # result = testdir.runpytest(*option.args)
    # assert result.ret == 0
    # assert result.parseoutcomes()['xfailed'] == 1
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, xfailed=1)


def test_failure_with_open_cards(testdir, option, monkeypatch_trello):
    '''Verifies when a test fails with open trello cards'''

    src = """
        import pytest
        @pytest.mark.trello(*%s)
        def test_func():
            assert False
        """ % OPEN_CARDS
    # testdir.makepyfile(src)
    # result = testdir.runpytest(*option.args)
    # assert result.ret == 0
    # assert result.parseoutcomes()['xfailed'] == 1
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, xfailed=1)


def test_failure_with_closed_card(testdir, option, monkeypatch_trello):
    '''Verifies when a test fails with a closed trello card'''

    src = """
        import pytest
        @pytest.mark.trello('%s')
        def test_func():
            assert False
        """ % CLOSED_CARDS[0]
    # testdir.makepyfile(src)
    # result = testdir.runpytest(*option.args)
    # assert result.ret == 1
    # assert result.parseoutcomes()['failed'] == 1
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, failed=1)


def test_failure_with_closed_cards(testdir, option, monkeypatch_trello):
    '''Verifies when a test fails with closed trello cards'''

    src = """
        import pytest
        @pytest.mark.trello(*%s)
        def test_func():
            assert False
        """ % CLOSED_CARDS
    # testdir.makepyfile(src)
    # result = testdir.runpytest(*option.args)
    # assert result.ret == 1
    # assert result.parseoutcomes()['failed'] == 1
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, failed=1)


def test_failure_with_open_and_closed_cards(testdir, option, monkeypatch_trello):
    '''Verifies test failure with open and closed trello cards'''

    src = """
        import pytest
        @pytest.mark.trello(*%s)
        def test_func():
            assert False
        """ % ALL_CARDS
    # testdir.makepyfile(src)
    # result = testdir.runpytest(*option.args)
    # assert result.ret == 0
    # assert result.parseoutcomes()['xfailed'] == 1
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, xfailed=1)


def test_skip_with_open_card(testdir, option, monkeypatch_trello):
    '''Verifies skipping with an open trello card'''

    src = """
        import pytest
        @pytest.mark.trello('%s', skip=True)
        def test_func():
            assert False
        """ % OPEN_CARDS[0]
    # testdir.makepyfile(src)
    # result = testdir.runpytest(*option.args)
    # assert result.ret == 0
    # assert result.parseoutcomes()['skipped'] == 1
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, skipped=1)


def test_skip_with_closed_card(testdir, option, monkeypatch_trello):
    '''Verifies test failure (skip=True) with a closed trello card'''

    src = """
        import pytest
        @pytest.mark.trello('%s', skip=True)
        def test_func():
            assert False
        """ % CLOSED_CARDS[0]
    # testdir.makepyfile(src)
    # result = testdir.runpytest(*option.args)
    # assert result.ret == 1
    # assert result.parseoutcomes()['failed'] == 1
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, failed=1)


def test_collection_reporter(testdir, option, monkeypatch_trello, capsys):
    '''Verifies trello marker collection'''

    src = """
        import pytest
        @pytest.mark.trello(*%s)
        def test_foo():
            assert True

        @pytest.mark.trello(*%s)
        def test_bar():
            assert False
        """ % (CLOSED_CARDS, OPEN_CARDS)
    # (items, result) = testdir.inline_genitems(src, *option.args)
    result = testdir.inline_runsource(src, *option.args)
    assert_outcome(result, passed=1, xfailed=1)

    stdout, stderr = capsys.readouterr()
    assert 'collected %s trello markers' % (len(CLOSED_CARDS) + len(OPEN_CARDS)) in stdout
