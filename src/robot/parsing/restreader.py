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
import os
from robot.errors import DataError
from .htmlreader import HtmlReader
from .txtreader import TxtReader

def RestReader():
    try:
        from docutils.core import publish_cmdline
        from docutils.parsers.rst import directives
        import docutils.core
    except ImportError:
        raise DataError("Using reStructuredText test data requires having "
                        "'docutils' module installed.")

    # Ignore custom sourcecode directives at least we use in reST sources.
    # See e.g. ug2html.py for an example how custom directives are created.
    ignorer = lambda *args: []
    ignorer.content = 1
    directives.register_directive('sourcecode', ignorer)

    class RestReader(HtmlReader):

        def read(self, rstfile, rawdata):
            doctree = docutils.core.publish_doctree(rstfile.read())

            def collect_robot_nodes(node, collected = []):
                robot_tagname = 'literal_block'
                robot_classes = ['code', 'robotframework']
                is_robot_node = (
                    node.tagname == robot_tagname
                    and node.attributes.get('classes') == robot_classes
                )
                if is_robot_node:
                    collected.append(node)
                else:
                    for node in node.children:
                        collected = collect_robot_nodes(node, collected)
                return collected

            robot_nodes = collect_robot_nodes(doctree)

            if robot_nodes:
                robot_data = "\n\n".join([node.rawsource for node in robot_nodes])
                txtfile = tempfile.NamedTemporaryFile()
                txtfile.write(robot_data)
                txtfile.seek(0)
                txtreader = TxtReader()
                return txtreader.read(txtfile, rawdata)
            else:
                htmlpath = self._rest_to_html(rstfile.name)
                htmlfile = None
                try:
                    htmlfile = open(htmlpath, 'rb')
                    return HtmlReader.read(self, htmlfile, rawdata)
                finally:
                    if htmlfile:
                        htmlfile.close()
                    os.remove(htmlpath)

        def _rest_to_html(self, rstpath):
            filedesc, htmlpath = tempfile.mkstemp('.html')
            os.close(filedesc)
            publish_cmdline(writer_name='html', argv=[rstpath, htmlpath])
            return htmlpath

    return RestReader()
