from StringIO import StringIO
import unittest
from robot.utils.asserts import assert_equals, assert_true
from robot.result.jsondatamodel import DataModel

class TestDataModelWrite(unittest.TestCase):

    def test_writing_datamodel_elements(self):
        lines = self._get_lines()
        assert_true(lines[0].startswith('window.output = {}'))
        assert_true(lines[1].startswith('window.output["'))
        assert_true(lines[-1].startswith('window.settings ='))

    def _get_lines(self, data=None, separator=None, split_threshold=None):
        output = StringIO()
        DataModel(data or {'baseMillis':100}).write_to(output, separator=separator, split_threshold=split_threshold)
        return output.getvalue().splitlines()

    def test_writing_datamodel_with_separator(self):
        lines = self._get_lines(separator='seppo\n')
        assert_true(len(lines) >= 2)
        self._assert_separators_in(lines, 'seppo')

    def _assert_separators_in(self, lines, separator):
        for index, line in enumerate(lines):
            if index % 2:
                assert_equals(line, separator)
            else:
                assert_true(line.startswith('window.'))

    def test_writing_datamodel_with_split_threshold_in_suite(self):
        suite = [1, [2, 3], [4, [5], [6, 7]], 8]
        lines = self._get_lines(data={'baseMillis':100, 'suite':suite},
                                split_threshold=2, separator='foo\n')
        parts = filter(lambda l: l.startswith('window.sPart'), lines)
        assert_equals(len(parts), 4)
        self._assert_separators_in(lines, 'foo')

    def test_splitting_output_integers(self):
        lines = self._get_lines(data={'baseMillis':100, 'integers':range(900)},
                                split_threshold=200, separator='\n')
        parts = [l for l in lines if l.startswith('window.output["int')]
        assert_equals(len(parts), 6)
        self._assert_separators_in(lines, '')

    def test_splitting_output_integers(self):
        lines = self._get_lines(data={'baseMillis':100, 'strings':['data' for _ in range(100)]},
                                split_threshold=9, separator='?\n')
        parts = [l for l in lines if l.startswith('window.output["strings')]
        assert_equals(len(parts), 13)
        self._assert_separators_in(lines, '?')