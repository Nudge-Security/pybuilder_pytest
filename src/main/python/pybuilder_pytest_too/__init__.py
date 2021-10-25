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
import os
import tempfile

import pytest
from sys import path as sys_path

from pybuilder.core import task, init, use_plugin, Logger
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.unittest_plugin \
    import _register_test_and_source_path_and_return_test_dir \
    as push_test_path_to_syspath

__author__ = 'Alexey Sanko'

from pybuilder.utils import read_file

use_plugin("python.core")


@init
def initialize_pytest_plugin(project):
    """ Init default plugin project properties. """
    project.build_depends_on('pytest')
    project.build_depends_on('pytest-cov')
    project.set_property_if_unset("dir_source_pytest_python", "src/unittest/python")
    project.set_property_if_unset("pytest_extra_args", [])
    project.set_property_if_unset("pytest_python_env", "build")


@task
def run_unit_tests(project, logger:Logger,reactor):
    """ Call pytest for the sources of the given project. """
    logger.info('pytest: Run unittests.')
    test_dir = push_test_path_to_syspath(project, sys_path, 'pytest')
    extra_args = [project.expand(prop) for prop in project.get_property("pytest_extra_args")]
    try:
        pytest_args = [test_dir] + (extra_args if extra_args else [])
        if project.get_property('verbose'):
            pytest_args.append('-s')
            pytest_args.append('-v')
        env_ = reactor.python_env_registry[project.get_property("unittest_python_env")]
        cmd_args = [env_.executable]
        cmd_args.extend(['-m','pytest'])
        cmd_args.extend(pytest_args)
        with tempfile.NamedTemporaryFile() as outfile:
            error_file_name = "{0}.err".format(outfile.name)
            ret = env_.execute_command(cmd_args,outfile.name,env=os.environ, cwd=project.get_property('dir_source_pytest_python'))
            error_file_lines = read_file(error_file_name)
            outfile_lines = read_file(outfile.name)
            for line in error_file_lines:
                logger.error(line)
            for line in outfile_lines:
                logger.info(line)
            if ret:
                raise BuildFailedException('pytest: unittests failed')
            else:
                logger.info('pytest: All unittests passed.')
    except Exception:
        raise
