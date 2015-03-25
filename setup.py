import os
import sys
import glob
import shutil
from setuptools import setup, Command
from setuptools.command.test import test as TestCommand
from pytest_trello import __version__, __author__, __author_email__

if sys.version_info < (3, 0):
    from ConfigParser import ConfigParser
else:
    from configparser import ConfigParser


class ToxTest(TestCommand):
    """Custom setup.py test command implementation using tox runner."""
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['--recreate -vv']
        self.test_suite = True

        def run_tests(self):
            # import here, cause outside the eggs aren't loaded
            import detox.main
            errno = detox.main.main(self.test_args)
            sys.exit(errno)


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

        # read pytest.addopts from setup.cfg
        if not self.pytest_args:
            cp = ConfigParser()
            cp.read('setup.cfg')
            self.pytest_args = cp.get('pytest', 'addopts')

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


class CleanCommand(Command):
    description = "Custom clean command that forcefully removes dist/build directories"
    user_options = []

    def initialize_options(self):
        self.cwd = None

    def finalize_options(self):
        self.cwd = os.getcwd()

    def run(self):
        assert os.getcwd() == self.cwd, 'Must be in package root: %s' % self.cwd

        # List of things to remove
        rm_list = list()

        # Find any .pyc files or __pycache__ dirs
        for root, dirs, files in os.walk(self.cwd, topdown=False):
            for fname in files:
                if fname.endswith('.pyc') and os.path.isfile(os.path.join(root, fname)):
                    rm_list.append(os.path.join(root, fname))
            if root.endswith('__pycache__'):
                rm_list.append(root)

        # Find egg's
        for egg_dir in glob.glob('*.egg') + glob.glob('*egg-info'):
            rm_list.append(egg_dir)

        # Zap!
        for rm in rm_list:
            if self.verbose:
                print("Removing '%s'" % rm)
            if os.path.isdir(rm):
                if not self.dry_run:
                    shutil.rmtree(rm)
            else:
                if not self.dry_run:
                    os.remove(rm)


def long_description(*paths):
    '''Returns a RST formated string.
    '''
    result = ''

    # attempt to import pandoc
    try:
        import pypandoc
    except ImportError:
        return result

    # attempt md -> rst conversion
    try:
        for path in paths:
            result += pypandoc.convert(
                path, 'rst', format='markdown'
            )
    except (OSError, IOError):
        return result

    return result


setup(
    name="pytest-trello",
    version=__version__,
    description='Plugin for py.test that integrates trello using markers',
    long_description=long_description('README.md', 'HISTORY.md'),
    license='MIT',
    keywords='py.test pytest trello',
    author=__author__,
    author_email=__author_email__,
    url='http://github.com/jlaska/pytest-trello',
    platforms='any',
    packages=['pytest_trello'],
    entry_points={
        'pytest11': [
            'pytest-trello = pytest_trello.plugin'
        ],
    },
    zip_safe=False,
    tests_requires=['tox', 'trello', 'pytest'],
    install_requires=['trello', 'pytest', 'PyYAML'],
    setup_requires=['flake8'],
    cmdclass={
        # 'test': ToxTest,
        'test': PyTest,
        'clean': CleanCommand,
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Utilities',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7 ',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
)
