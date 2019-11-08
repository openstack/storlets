# Copyright (c) 2010-2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import unittest
import tempfile
import subprocess
import nbformat
import six


COULD_BE_CHANGED = ['x-storlet-generated-from-account',
                    'x-trans-id',
                    'x-openstack-request-id',
                    'x-storlet-generated-from-last-modified',
                    'last-modified',
                    'x-timestamp',
                    'date', ]


class TestJupyterExcecution(unittest.TestCase):
    def _run_notebook(self, path):
        """Execute a notebook via nbconvert and collect output.
        :returns (parsed nb object, execution errors)
        """
        with tempfile.NamedTemporaryFile(suffix=".ipynb") as fout:
            args = ["jupyter", "nbconvert", "--to", "notebook", "--execute",
                    "--ExecutePreprocessor.timeout=60",
                    "--output", fout.name, path]
            try:
                subprocess.check_output(args, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                # Note that CalledProcessError will have stdout/stderr in py3
                # instead of output attribute
                self.fail('jupyter nbconvert fails with:\n'
                          'STDOUT: %s\n' % (e.output))

            fout.seek(0)
            nb = nbformat.read(fout, nbformat.current_nbformat)

            # gather all error messages in all cells in the notebook
            errors = [output for cell in nb.cells if "outputs" in cell
                      for output in cell["outputs"]
                      if output.output_type == "error"]

            return nb, errors

    def _clear_text_list(self, node):
        """
        convert a notebook cell to text list like ["a", "b"]
        N.B. each text will be striped
        """
        texts = list()
        if 'text' in node:
            for line in node['text'].split('\n'):
                if line:
                    texts.append(line.strip())
            return texts

        return None

    def _flatten_output_text(self, notebook):
        """
        This helper method make the notebook output cells flatten to a single
        direction list.
        """
        output_text_list = []
        for cell in notebook.cells:
            for output in cell.get("outputs", []):
                output_text_list.extend(self._clear_text_list(output))
        return output_text_list

    def test_notebook(self):
        test_path = os.path.abspath(__file__)
        test_dir = os.path.dirname(test_path)
        original_notebook = os.path.join(test_dir, 'test_notebook.ipynb')

        with open(original_notebook) as f:
            original_nb = nbformat.read(f, nbformat.current_nbformat)
        expected_output = self._flatten_output_text(original_nb)
        got_nb, errors = self._run_notebook(original_notebook)
        self.assertFalse(errors)
        got = self._flatten_output_text(got_nb)
        self._assert_output(expected_output, got)

    def _assert_output(self, expected_output, got):
        for expected_line, got_line in zip(expected_output, got):
            try:
                expected_line = eval(expected_line)
                got_line = eval(got_line)
            except (NameError, SyntaxError, AttributeError):
                # sanity, both line should be string type
                self.assertIsInstance(expected_line, six.string_types)
                self.assertIsInstance(got_line, six.string_types)
                # this is for normal text line (NOT json dict)
                self.assertEqual(expected_line, got_line)
            else:
                if isinstance(expected_line, dict) and \
                        isinstance(got_line, dict):
                    expected_and_got = zip(
                        sorted(expected_line.items()),
                        sorted(got_line.items()))
                    for (expected_key, expected_value), (got_key, got_value) in \
                            expected_and_got:
                        self.assertEqual(expected_key, got_key)
                        if expected_key in COULD_BE_CHANGED:
                            # TODO(kota_): make more validation for each format
                            continue
                        else:
                            self.assertEqual(expected_value, got_value)
                else:
                    self.assertEqual(expected_line, got_line)


if __name__ == '__main__':
    unittest.main()
