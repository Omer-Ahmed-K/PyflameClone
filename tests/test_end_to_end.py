# Copyright 2016 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import pytest
import subprocess
import re


IDLE_RE = re.compile(r'^\(idle\) \d+$')
FLAMEGRAPH_RE = re.compile(r'^\S+ \d+$')
TS_IDLE_RE = re.compile(r'\(idle\)')
# Matches strings of the form
# './tests/sleeper.py:<module>:31;./tests/sleeper.py:main:26;'
TS_FLAMEGRAPH_RE = re.compile(r'[^[^\d]+\d+;]*')
TS_RE = re.compile(r'\d+')


@contextlib.contextmanager
def proc(test_file):
    # start the process and wait for it to print its pid... we explicitly do
    # this instead of using the pid attribute so we can ensure that the process
    # is initialized
    proc = subprocess.Popen(
        ['python', './tests/%s' % (test_file,)], stdout=subprocess.PIPE)
    proc.stdout.readline()

    try:
        yield proc
    finally:
        proc.kill()


@pytest.yield_fixture
def dijkstra():
    with proc('dijkstra.py') as p:
        yield p


@pytest.yield_fixture
def sleeper():
    with proc('sleeper.py') as p:
        yield p


@pytest.yield_fixture
def exit_early():
    with proc('exit_early.py') as p:
        yield p


def test_monitor(dijkstra):
    """Basic test for the monitor mode."""
    proc = subprocess.Popen(['./src/pyflame', str(dijkstra.pid)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    assert not err
    assert proc.returncode == 0
    lines = out.split('\n')
    assert lines.pop(-1) == ''  # output should end in a newline
    for line in lines:
        assert FLAMEGRAPH_RE.match(line) is not None


def test_idle(sleeper):
    """Basic test for idle processes."""
    proc = subprocess.Popen(['./src/pyflame', str(sleeper.pid)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    assert not err
    assert proc.returncode == 0
    lines = out.split('\n')
    assert lines.pop(-1) == ''  # output should end in a newline
    has_idle = False
    for line in lines:
        assert FLAMEGRAPH_RE.match(line) is not None
        if IDLE_RE.match(line):
            has_idle = True
    assert has_idle


def test_exit_early(exit_early):
    proc = subprocess.Popen(['./src/pyflame', '-s', '10', str(exit_early.pid)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    assert not err
    assert proc.returncode == 0
    lines = out.split('\n')
    assert lines.pop(-1) == ''  # output should end in a newline
    for line in lines:
        assert FLAMEGRAPH_RE.match(line) or IDLE_RE.match(line)


def test_exclude_idle(sleeper):
    """Basic test for idle processes."""
    proc = subprocess.Popen(['./src/pyflame', '-x', str(sleeper.pid)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    assert not err
    assert proc.returncode == 0
    lines = out.split('\n')
    assert lines.pop(-1) == ''  # output should end in a newline
    for line in lines:
        assert FLAMEGRAPH_RE.match(line) is not None
        assert not IDLE_RE.match(line)


def test_include_ts(sleeper):
    """Basic test for timestamp processes."""
    proc = subprocess.Popen(['./src/pyflame', '-t', str(sleeper.pid)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    assert not err
    assert proc.returncode == 0
    lines = out.split('\n')
    assert lines.pop(-1) == ''  # output should end in a newline
    for line in lines:
        assert (TS_FLAMEGRAPH_RE.match(line) or
                TS_RE.match(line) or TS_IDLE_RE.match(line))


def test_include_ts_exclude_idle(sleeper):
    """Basic test for timestamp processes."""
    proc = subprocess.Popen(['./src/pyflame', '-t', '-x',  str(sleeper.pid)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    assert not err
    assert proc.returncode == 0
    lines = out.split('\n')
    assert lines.pop(-1) == ''  # output should end in a newline
    for line in lines:
        assert not TS_IDLE_RE.match(line)
        assert (TS_FLAMEGRAPH_RE.match(line) or TS_RE.match(line))
