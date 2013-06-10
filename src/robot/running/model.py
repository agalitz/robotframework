#  Copyright 2008-2013 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from robot import model
from robot.conf import RobotSettings
from robot.output import LOGGER, Output, pyloggingconf
from robot.utils import setter
from robot.variables import init_global_variables

from .namespace import IMPORTER
from .randomizer import Randomizer
from .runner import Runner
from .signalhandler import STOP_SIGNAL_MONITOR


# TODO: This module should be turned into a package with submodules.
# No time for that prior to 2.8, but ii ought to be safe also in 2.8.x.
# Important to check that references in API docs don't break.


class Keyword(model.Keyword):
    __slots__ = ['assign']
    message_class = None  # TODO: Remove from base model?

    def __init__(self, name='', args=(), assign=(), type='kw'):
        """Running model for single keyword.

        :ivar name: Name of the keyword.
        :ivar args: Arguments for the keyword.
        :ivar assign: Variables to be assigned.
        :ivar type: Keyword type. Either 'kw', 'setup', or 'teardown'
        """
        model.Keyword.__init__(self, name=name, args=args, type=type)
        self.assign = assign

    def is_for_loop(self):
        return False

    def is_comment(self):
        return False

    @property
    def keyword(self):
        return self.name


class ForLoop(Keyword):
    __slots__ = ['range']
    keyword_class = Keyword

    def __init__(self, vars, items, range):
        Keyword.__init__(self, assign=vars, args=items, type='for')
        self.range = range

    @property
    def vars(self):
        return self.assign

    @property
    def items(self):
        return self.args

    def is_for_loop(self):
        return True

    @property
    def steps(self):
        return self.keywords


class TestCase(model.TestCase):
    __slots__ = ['template']
    keyword_class = Keyword

    def __init__(self, name='', doc='', tags=None, timeout=None, template=None):
        """Running model for single test case.

        :ivar name: Name of the test case.
        :ivar doc: Documentation of the test case.
        :ivar tags: Tags of the test case.
        :ivar timeout: Timeout limit of the test case
        :ivar template: Name of the keyword that has been used as template
            when building the test. `None` if no template used.
        """
        model.TestCase.__init__(self, name, doc, tags, timeout)
        self.template = template

    @setter
    def timeout(self, timeout):
        return Timeout(*timeout) if timeout else None


class TestSuite(model.TestSuite):
    __slots__ = []
    test_class = TestCase
    keyword_class = Keyword

    def __init__(self,  name='', doc='', metadata=None, source=None):
        """Running model for single test suite.

        :ivar parent: Parent :class:`TestSuite` or `None`.
        :ivar name: Test suite name.
        :ivar doc: Test suite documentation.
        :ivar metadata: Test suite metadata as a dictionary.
        :ivar source: Path to the source file or directory.
        :ivar suites: Child suites.
        :ivar tests: A list of :class:`~.testcase.TestCase` instances.
        :ivar keywords: A list containing setup and teardown as
            :class:`~robot.running.model.Keyword` objects.
        :ivar imports: Imports the suite contains.
        :ivar user_keywords: User keywords defined in the same file as the
            suite. **Likely to change or to be removed.**
        :ivar variables: Variables defined in the same file as the suite.
            **Likely to change or to be removed.**
        """
        model.TestSuite.__init__(self, name, doc, metadata, source)
        self.imports = []
        self.user_keywords = []
        self.variables = []

    @setter
    def imports(self, imports):
        return model.Imports(self.source, imports)

    @setter
    def user_keywords(self, keywords):
        return model.ItemList(UserKeyword, items=keywords)

    @setter
    def variables(self, variables):
        return model.ItemList(Variable, {'source': self.source}, items=variables)

    def configure(self, randomize_suites=False, randomize_tests=False,
                  **options):
        model.TestSuite.configure(self, **options)
        self.randomize(randomize_suites, randomize_tests)

    def randomize(self, suites=True, tests=True):
        """Randomizes the order of suites and/or tests, recursively."""
        self.visit(Randomizer(suites, tests))

    def run(self, settings=None, **options):
        """
        Executes the tests based based the given ``settings`` or ``options``.

        :param settings: :class:`~robot.conf.settings.RobotSettings` object
            to configure test execution.
        :param options: Used to construct new
            :class:`~robot.conf.settings.RobotSettings` object if ``settings``
            are not given.

        Options are given as keyword arguments and their names are same as
        long command line options except without hyphens.

        The effective options are all that relate to the actual
        execution of tests. This means, that filtering and writing log,
        report or XUnit is not affected by the given options.

        Example::

            suite = TestSuite(...)
            ...
            result = suite.run(
                skipteardownonexit=True,
                randomize_suites=True,
                output='my_output.xml'
            )

        Options that can be given on the command line multiple times can be
        passed as lists like `include=['tag1', 'tag2']`.

        Example::

            suite = TestSuite(...)
            ...
            result = suite.run(include=['tag1, 'tag2'])

        If such option is used only once, it can be given also as
        a single string like `include='tag'`.

        Example::

            suite = TestSuite(...)
            ...
            result = suite.run(include='tag')

        To capture stdout and/or stderr streams, pass open file objects in as
        special keyword arguments `stdout` and `stderr`, respectively.

        Example::

            suite = TestSuite(...)
            ...
            stdout_file = open('test_output.txt', 'w')
            stderr_file = open('test_errors.txt', 'w')
            result = suite.run(stdout=stdout_file, stderr=stderr_file)

        Please see examples at :mod:`running API <robot.running>`
        on how to create runnable test suites.
        """
        STOP_SIGNAL_MONITOR.start()
        IMPORTER.reset()
        settings = settings or RobotSettings(options)
        pyloggingconf.initialize(settings['LogLevel'])
        init_global_variables(settings)
        output = Output(settings)
        runner = Runner(output, settings)
        self.visit(runner)
        output.close(runner.result)
        return runner.result


class Variable(object):

    def __init__(self, name, value, source=None):
        # TODO: check name and value
        self.name = name
        self.value = value
        self.source = source

    def report_invalid_syntax(self, message, level='ERROR'):
        LOGGER.write("Error in file '%s': Setting variable '%s' failed: %s"
                     % (self.source or '<unknown>', self.name, message), level)


class Timeout(object):

    def __init__(self, value, message=None):
        self.value = value
        self.message = message

    def __str__(self):
        return self.value


class UserKeyword(object):
    # TODO: In 2.9:
    # - Teardown should be handled as a keyword like with tests and suites.
    # - Timeout should be handled consistently with tests.
    # - Also resource files should use these model objects.

    def __init__(self, name, args=(), doc='', return_=None, timeout=None,
                 teardown=None):
        self.name = name
        self.args = args
        self.doc = doc
        self.return_ = return_ or ()
        self.teardown = None
        self.timeout = timeout
        self.teardown = teardown
        self.keywords = []

    @setter
    def keywords(self, keywords):
        return model.ItemList(Keyword, items=keywords)

    # Compatibility with parsing model. Should be removed in 2.9.
    @property
    def steps(self):
        return self.keywords
