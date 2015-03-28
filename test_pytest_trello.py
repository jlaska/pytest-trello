# -*- coding: utf-8 -*-
import pytest


pytest_plugins = 'pytester',

# TODO - mock the following
OPEN_CARDS = ['https://trello.com/c/NIRpzVDM', 'https://trello.com/c/VWrInnH8']
CLOSED_CARDS = ['https://trello.com/c/OlTKlSQE', 'https://trello.com/c/BLxoci6b']
ALL_CARDS = OPEN_CARDS + CLOSED_CARDS


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


@pytest.fixture()
def option(request):
    return PyTestOption(request.config)


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


def test_success_with_open_card(testdir, option):
    '''Verifies when a test succeeds with an open trello card'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello('%s')
        def test_func():
            assert True
        """ % OPEN_CARDS[0])
    result = testdir.runpytest(*option.args)
    assert result.ret == 0
    assert result.parseoutcomes()['xpassed'] == 1


def test_success_with_open_cards(testdir, option):
    '''Verifies when a test succeeds with open trello cards'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello(*%s)
        def test_func():
            assert True
        """ % OPEN_CARDS)
    result = testdir.runpytest(*option.args)
    assert result.ret == 0
    assert result.parseoutcomes()['xpassed'] == 1


def test_failure_with_open_card(testdir, option):
    '''Verifies when a test fails with an open trello card'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello('%s')
        def test_func():
            assert False
        """ % OPEN_CARDS[0])
    result = testdir.runpytest(*option.args)
    assert result.ret == 0
    assert result.parseoutcomes()['xfailed'] == 1


def test_failure_with_open_cards(testdir, option):
    '''Verifies when a test fails with open trello cards'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello(*%s)
        def test_func():
            assert False
        """ % OPEN_CARDS)
    result = testdir.runpytest(*option.args)
    assert result.ret == 0
    assert result.parseoutcomes()['xfailed'] == 1


def test_failure_with_closed_card(testdir, option):
    '''Verifies when a test fails with a closed trello card'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello('%s')
        def test_func():
            assert False
        """ % CLOSED_CARDS[0])
    result = testdir.runpytest(*option.args)
    assert result.ret == 1
    assert result.parseoutcomes()['failed'] == 1


def test_failure_with_closed_cards(testdir, option):
    '''Verifies when a test fails with closed trello cards'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello(*%s)
        def test_func():
            assert False
        """ % CLOSED_CARDS)
    result = testdir.runpytest(*option.args)
    assert result.ret == 1
    assert result.parseoutcomes()['failed'] == 1


def test_failure_with_open_and_closed_cards(testdir, option):
    '''Verifies test failure with open and closed trello cards'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello(*%s)
        def test_func():
            assert False
        """ % ALL_CARDS)
    result = testdir.runpytest(*option.args)
    assert result.ret == 0
    assert result.parseoutcomes()['xfailed'] == 1


def test_skip_with_open_card(testdir, option):
    '''Verifies skipping with an open trello card'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello('%s', skip=True)
        def test_func():
            assert False
        """ % OPEN_CARDS[0])
    result = testdir.runpytest(*option.args)
    assert result.ret == 0
    assert result.parseoutcomes()['skipped'] == 1


def test_skip_with_closed_card(testdir, option):
    '''Verifies test failure (skip=True) with a closed trello card'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello('%s', skip=True)
        def test_func():
            assert False
        """ % CLOSED_CARDS[0])
    result = testdir.runpytest(*option.args)
    assert result.ret == 1
    assert result.parseoutcomes()['failed'] == 1


def test_collection_reporter(testdir, option):
    '''Verifies trello marker collection'''

    testdir.makepyfile("""
        import pytest
        @pytest.mark.trello(*%s)
        def test_foo():
            assert True

        @pytest.mark.trello(*%s)
        def test_bar():
            assert False
        """ % (CLOSED_CARDS, OPEN_CARDS))
    result = testdir.runpytest(*option.args)
    assert result.ret == 0
    result.stdout.fnmatch_lines([
        'collected %s trello markers' % (len(CLOSED_CARDS) + len(OPEN_CARDS)),
    ])
