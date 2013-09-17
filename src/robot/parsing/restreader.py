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

import tempfile
from robot.errors import DataError
from .htmlreader import HtmlReader
from .txtreader import TxtReader


def RestReader():
    try:
        import docutils.core
        from docutils.parsers.rst import DirectiveError
        from docutils.parsers.rst.directives import register_directive
        from docutils.parsers.rst.directives import body
    except ImportError:
        raise DataError("Using reStructuredText test data requires having "
                        "'docutils' module installed.")

    # Ignore custom sourcecode directives at least we use in reST sources.
    # See e.g. ug2html.py for an example how custom directives are created.
    ignorer = lambda *args: []
    ignorer.content = 1
    register_directive('sourcecode', ignorer)

    # Override default CodeBlock with a derived custom directive, which can
    # capture Robot Framework test suite snippets and support execution also
    # when Pygments is not installed or it is not new enough to support
    # robotframework-language.
    class RobotAwareCodeBlock(body.CodeBlock):
        def run(self):
            if u'robotframework' in self.arguments:
                document = self.state_machine.document
                robot_source = u'\n'.join(self.content)
                if not hasattr(document, '_robot_source'):
                    document._robot_source = robot_source
                else:
                    document._robot_source += u'\n' + robot_source
            try:
                return super(RobotAwareCodeBlock, self).run()
            except DirectiveError:
                # Pygments was not found or it was not recent enough
                # robotframework as a language. Reset language attribute and
                # try again.
                self.arguments = []
                return super(RobotAwareCodeBlock, self).run()
    register_directive('code', RobotAwareCodeBlock)

    class RestReader:

        def read(self, rstfile, rawdata):
            doctree = docutils.core.publish_doctree(rstfile.read())

            if hasattr(doctree, '_robot_source'):
                txtfile = tempfile.NamedTemporaryFile(suffix='.robot')
                txtfile.write(doctree._robot_source.encode('utf-8'))
                txtfile.seek(0)
                txtreader = TxtReader()
                try:
                    return txtreader.read(txtfile, rawdata)
                finally:
                    txtfile.close()
            else:
                htmlfile = tempfile.NamedTemporaryFile(suffix='.html')
                htmlfile.write(docutils.core.publish_from_doctree(
                    doctree, writer_name='html',
                    settings_overrides={'output_encoding': 'utf-8'}))
                htmlfile.seek(0)
                htmlreader = HtmlReader()
                try:
                    return htmlreader.read(htmlfile, rawdata)
                finally:
                    htmlfile.close()

    return RestReader()
