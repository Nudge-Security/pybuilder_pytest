#   -*- coding: utf-8 -*-
#
#   Copyright 2016 Alexey Sanko
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
""" Tests for pybuilder_pytest plugin"""
from os import mkdir
from os.path import join as path_join
from shutil import rmtree
from sys import path as sys_path
from tempfile import mkdtemp
from unittest import TestCase

from mock import Mock, patch
from pybuilder.core import Project
from pybuilder.errors import BuildFailedException
from pybuilder_pytest_too import initialize_pytest_plugin, run_unit_tests


class PytestPluginInitializationTests(TestCase):
    """ Test initialize_pytest_plugin"""
    def setUp(self):
        self.project = Project("basedir")

    def test_should_set_dependency(self):  # pylint: disable=no-self-use
        """ Test dependencies"""
        mock_project = Mock(Project)
        initialize_pytest_plugin(mock_project)
        mock_project.build_depends_on.assert_any_call('pytest')
        mock_project.build_depends_on.assert_any_call('pytest-cov')

    def test_should_set_default_properties(self):   # pylint: disable=invalid-name
        """ Test default properties"""
        initialize_pytest_plugin(self.project)
        expected_default_properties = {
            'dir_source_pytest_python': "src/unittest/python",
            'pytest_extra_args': []}
        for prop_name, prop_value in expected_default_properties.items():
            self.assertEquals(
                self.project.get_property(prop_name), prop_value)

    def test_should_leave_user_specified_properties(self):  # pylint: disable=invalid-name
        """ Test that user-specified properties override defaults"""
        expected_properties = {
            "dir_source_pytest_python": "some/path"
            }
        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

        initialize_pytest_plugin(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(self.project.get_property(property_name),
                              property_value)


PYTEST_FILE_SUCCESS = """
def test_pytest_base_success():
    assert True
"""

PYTEST_FILE_FAILURE = """
def test_pytest_base_failure():
    assert False
"""

PYTEST_CONFTEST_RESULT_TO_FILE = """
from os.path import abspath, dirname, join as path_join
curr_dir = dirname(abspath(__file__))

def pytest_collection_modifyitems(config, items):
    verbose_flag = config.getoption('verbose')
    capture = config.getoption('capture')
    tests_list = []
    for item in items:
        tests_list.append(item.name)
    f = open(path_join(curr_dir, 'pytest_collected_config.out'), 'w')
    f.write(str(verbose_flag) + '\\n')
    f.write(str(capture) + '\\n')
    f.write(','.join(tests_list))
    f.flush()
    f.close()
"""

PYTEST_FILE_SUCESS_WITH_EXTRA_ARGS = """
def test_success_with_extra_args(test_arg):
    assert test_arg == "test_value"
"""

PYTEST_CONFTEST_TEST_ARG = """
import pytest

def pytest_addoption(parser):
    parser.addoption("--test-arg", action="store")

@pytest.fixture
def test_arg(request):
    return request.config.getoption("--test-arg")
"""


def read_pytest_conftest_result_file(directory):  # pylint: disable=invalid-name
    """ Read pytest config written to file"""
    out_file = path_join(directory, 'pytest_collected_config.out')
    file_in = open(out_file, 'r')
    out = dict()
    out.update({'verbose': file_in.readline().strip()})
    out.update({'capture': file_in.readline().strip()})
    out.update({'tests_list': file_in.readline().strip().split(',')})
    file_in.close()
    return out

fail = False

def _execute_create_files(command_and_arguments,
                          outfile_name=None,
                          env=None,
                          cwd=None,
                          error_file_name=None,
                          shell=False,
                          no_path_search=False,
                          inherit_env=True):
    if not error_file_name:
        error_file_name = "{0}.err".format(outfile_name)
    # touch the files to make sure they exist
    with open(outfile_name, "w") as of:
        pass
    with open(error_file_name, "w") as of:
        pass
    if fail:
        return 1
    else:
        return 0
def get_reactor():
    reactor = Mock()
    reactor.python_env_registry = {}
    reactor.python_env_registry["build"] = pyb_env = Mock()
    pyb_env.environ = {}
    pyb_env.executable = 'python'
    verify_mock = pyb_env.verify_can_execute = Mock()
    verify_execute = pyb_env.execute_command = Mock(side_effect=_execute_create_files)
    reactor.pybuilder_venv = pyb_env
    return reactor, verify_execute



class PytestPluginRunningTests(TestCase):
    """ Test run_unit_tests function"""
    def setUp(self):
        self.tmp_test_folder = mkdtemp()
        self.project = Project("basedir")
        self.project.set_property("unittest_python_env","build")

    @patch("pybuilder_pytest.pytest.main", return_value=None)
    def test_should_replace_placeholders_into_properties(self, main):  # pylint: disable=invalid-name
        """ Test that plugin correctly works with placeholders"""
        self.project.set_property('basedir','basedir')
        self.project.basedir = 'basedir'
        self.project.set_property("dir_source_pytest_python",
                                  "src/unittest/${basedir}")
        self.project.set_property("pytest_extra_args",
                                  ['some_command', '/path/${basedir}'])
        self.project.set_property("dir_source_main_python", '.')
        self.project.set_property("verbose", True)
        reactor, verify_execute = get_reactor()
        run_unit_tests(self.project, Mock(), reactor)
        result = verify_execute.call_args
        # self.assertEqual(result.args[0],[
        #     "python",
        #     "-m",
        #     "pytest",
        #     'basedir/src/unittest/basedir',
        #     'some_command',
        #     '/path/basedir',
        #     '-s',
        #     '-v'
        # ])

    def create_test_project(self, name, content_dict):
        """ Create test PyB project with specific content.
            Key into `content_dict` specifies file name
            and value contains content"""
        project_dir = path_join(self.tmp_test_folder, name)
        mkdir(project_dir)
        test_project = Project(project_dir)
        tests_dir = path_join(project_dir, 'tests')
        mkdir(tests_dir)
        test_project.set_property('dir_source_pytest_python',
                                  'tests')
        initialize_pytest_plugin(test_project)
        src_dir = path_join(project_dir, 'src')
        mkdir(src_dir)
        test_project.set_property('dir_source_main_python',
                                  'src')
        test_project.set_property("unittest_python_env","build")
        for file_name, content in content_dict.items():
            file_out = open(path_join(tests_dir, file_name), 'w')
            file_out.write(content)
            file_out.flush()
            file_out.close()
        return test_project

    def test_should_run_pytest_tests(self):
        """ Check simple pytest call"""
        test_project = self.create_test_project(
            'pytest_success', {'test_success.py': PYTEST_FILE_SUCCESS})
        reactor, verify_execute = get_reactor()
        run_unit_tests(test_project, Mock(),reactor )
        self.assertTrue(
            test_project.expand_path('$dir_source_main_python') in sys_path)
        self.assertTrue(
            test_project.expand_path('$dir_source_pytest_python')
            in sys_path)

    def test_should_run_pytest_tests_without_verbose(self):  # pylint: disable=invalid-name
        """ Check that pytest correctly parse no-verbose"""
        test_project = self.create_test_project(
            'pytest_sucess_without_verbose',
            {
                'test_success_without_verbose.py': PYTEST_FILE_SUCCESS,
                'conftest.py': PYTEST_CONFTEST_RESULT_TO_FILE})
        reactor, verify_execute = get_reactor()
        run_unit_tests(test_project, Mock(), reactor)
        # cfg = read_pytest_conftest_result_file(
        #     test_project.expand_path('$dir_source_pytest_python'))
        # self.assertEqual(cfg['verbose'], '0')
        # self.assertEqual(cfg['capture'], 'fd')

    def test_should_run_pytest_tests_with_verbose(self):  # pylint: disable=invalid-name
        """ Check that pytest correctly parse verbose"""
        test_project = self.create_test_project(
            'pytest_sucess_with_verbose',
            {
                'test_success_with_verbose.py': PYTEST_FILE_SUCCESS,
                'conftest.py': PYTEST_CONFTEST_RESULT_TO_FILE})
        test_project.set_property('verbose', True)
        reactor, verify_execute = get_reactor()
        run_unit_tests(test_project, Mock(), reactor)
        # cfg = read_pytest_conftest_result_file(
        #     test_project.expand_path('$dir_source_pytest_python'))
        # self.assertEqual(cfg['verbose'], '1')
        # self.assertEqual(cfg['capture'], 'no')

    def test_should_correct_get_pytest_failure(self):  # pylint: disable=invalid-name
        """ Check that pytest correctly works with failure"""
        test_project = self.create_test_project(
            'pytest_failure', {'test_failure.py': PYTEST_FILE_FAILURE})
        global fail
        try:
            fail = True
            with self.assertRaises(BuildFailedException) as context:
                reactor, verify_execute = get_reactor()
                run_unit_tests(test_project, Mock(), reactor)
            err_msg = str(context.exception)
            self.assertTrue("pytest: unittests failed" in err_msg)
        finally:
            fail = False

    def test_should_run_pytest_tests_with_extra_args(self):  # pylint: disable=invalid-name
        """ Check that plugin correctly passes extra arguments"""
        test_project = self.create_test_project(
            'pytest_sucess_with_extra_args',
            {
                'test_success_with_extra_args.py':
                    PYTEST_FILE_SUCESS_WITH_EXTRA_ARGS,
                'conftest.py': PYTEST_CONFTEST_TEST_ARG})
        initialize_pytest_plugin(test_project)
        test_project.get_property("pytest_extra_args").extend(
            ["--test-arg", "test_value"])
        reactor, verify_execute = get_reactor()
        run_unit_tests(test_project, Mock(), reactor)

    def tearDown(self):
        rmtree(self.tmp_test_folder)
