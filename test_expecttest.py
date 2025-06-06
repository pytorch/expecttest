import doctest
import sys
import string
import shutil
import subprocess
import os
import textwrap
import traceback
import unittest
import tempfile
import runpy
from typing import Any, Dict, Tuple, Generator
from contextlib import contextmanager
from pathlib import Path

import hypothesis
from hypothesis.strategies import booleans, composite, integers, sampled_from, text

import expecttest


def sh(file: str, accept: bool = False) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    env = ""
    if accept:
        env = "EXPECTTEST_ACCEPT=1 "
    print(f"    $ {env}python {file}")
    r = subprocess.run(
        [sys.executable, file],
        capture_output=True,
        # NB: Always OVERRIDE EXPECTTEST_ACCEPT variable, so outer usage doesn't
        # get confused!
        env={**os.environ, "EXPECTTEST_ACCEPT": "1" if accept else ""},
        text=True,
    )
    if r.stderr:
        print(textwrap.indent(r.stderr, "    "))
    return r


@composite
def text_lineno(draw: Any) -> Tuple[str, int]:
    t = draw(text("a\n"))
    lineno = draw(integers(min_value=1, max_value=t.count("\n") + 1))
    return (t, lineno)


@contextmanager
def smoketest(name: str) -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as d:
        dst = Path(d) / "test.py"
        code_dir = Path(__file__).parent
        shutil.copy(
            code_dir / "smoketests" / name,
            dst,
        )
        yield str(dst)


class TestExpectTest(expecttest.TestCase):
    @hypothesis.given(text_lineno())
    def test_nth_line_ref(self, t_lineno: Tuple[str, int]) -> None:
        t, lineno = t_lineno
        hypothesis.event("lineno = {}".format(lineno))

        def nth_line_ref(src: str, lineno: int) -> int:
            xs = src.split("\n")[:lineno]
            xs[-1] = ""
            return len("\n".join(xs))

        self.assertEqual(expecttest.nth_line(t, lineno), nth_line_ref(t, lineno))

    @hypothesis.given(text(string.printable), booleans(), sampled_from(['"', "'"]))
    def test_replace_string_literal_roundtrip(
        self, t: str, raw: bool, quote: str
    ) -> None:
        if raw:
            hypothesis.assume(
                expecttest.ok_for_raw_triple_quoted_string(t, quote=quote)
            )
        prog = """\
        r = {r}{quote}placeholder{quote}
        r2 = {r}{quote}placeholder2{quote}
        r3 = {r}{quote}placeholder3{quote}
        """.format(
            r="r" if raw else "", quote=quote * 3
        )
        new_prog = expecttest.replace_string_literal(textwrap.dedent(prog), 2, 2, t)[0]
        ns: Dict[str, Any] = {}
        exec(new_prog, ns)
        msg = "program was:\n{}".format(new_prog)
        self.assertEqual(ns["r"], "placeholder", msg=msg)  # noqa: F821
        self.assertEqual(ns["r2"], expecttest.normalize_nl(t), msg=msg)  # noqa: F821
        self.assertEqual(ns["r3"], "placeholder3", msg=msg)  # noqa: F821

    def test_sample_lineno(self) -> None:
        prog = r"""
single_single('''0''')
single_multi('''1''')
multi_single('''\
2
''')
multi_multi_less('''\
3
4
''')
multi_multi_same('''\
5
''')
multi_multi_more('''\
6
''')
different_indent(
    RuntimeError,
    '''7'''
)
"""
        edits = [
            (2, 2, "a"),
            (3, 3, "b\n"),
            (4, 6, "c"),
            (7, 10, "d\n"),
            (11, 13, "e\n"),
            (14, 16, "f\ng\n"),
            (17, 20, "h"),
        ]
        history = expecttest.EditHistory()
        fn = "not_a_real_file.py"
        for start_lineno, end_lineno, actual in edits:
            start_lineno = history.adjust_lineno(fn, start_lineno)
            end_lineno = history.adjust_lineno(fn, end_lineno)
            prog, delta = expecttest.replace_string_literal(
                prog, start_lineno, end_lineno, actual
            )
            # NB: it doesn't really matter start/end you record edit at
            history.record_edit(fn, start_lineno, delta, actual)
        self.assertExpectedInline(
            prog,
            r"""
single_single('''a''')
single_multi('''\
b
''')
multi_single('''c''')
multi_multi_less('''\
d
''')
multi_multi_same('''\
e
''')
multi_multi_more('''\
f
g
''')
different_indent(
    RuntimeError,
    '''h'''
)
""",
        )

    def test_lineno_assumptions(self) -> None:
        def get_tb(s: str) -> traceback.StackSummary:
            return traceback.extract_stack(limit=2)

        tb1 = get_tb("")
        tb2 = get_tb(
            """a
b
c"""
        )

        assert isinstance(tb1[0].lineno, int)
        if expecttest.LINENO_AT_START:
            # tb2's stack starts on the next line
            self.assertEqual(tb1[0].lineno + 1, tb2[0].lineno)
        else:
            # starts at the end here
            self.assertEqual(tb1[0].lineno + 1 + 2, tb2[0].lineno)

    def test_smoketest_accept_twice(self) -> None:
        with smoketest("accept_twice.py") as test_py:
            r = sh(test_py)
            self.assertNotEqual(r.returncode, 0)
            r = sh(test_py, accept=True)
            self.assertExpectedInline(
                r.stdout.replace(test_py, "test.py"),
                """\
Accepting new output for __main__.Test.test_a at test.py:10
Skipping already accepted output for __main__.Test.test_a at test.py:10
Accepting new output for __main__.Test.test_b at test.py:21
""",
            )
            r = sh(test_py)
            self.assertEqual(r.returncode, 0)

    def test_smoketest_non_ascii(self) -> None:
        with smoketest("accept_non_ascii.py") as test_py:
            r = sh(test_py)
            self.assertNotEqual(r.returncode, 0)
            r = sh(test_py, accept=True)
            self.assertExpectedInline(
                r.stdout.replace(str(test_py), "test.py"),
                """\
Accepting new output for __main__.Test.test_a at test.py:10
Skipping already accepted output for __main__.Test.test_a at test.py:10
Accepting new output for __main__.Test.test_b at test.py:21
""",
            )
            r = sh(test_py)
            self.assertEqual(r.returncode, 0)

    def test_smoketest_no_unittest(self) -> None:
        with smoketest("no_unittest.py") as test_py:
            r = sh(test_py)
            self.assertNotEqual(r.returncode, 0)
            r = sh(test_py, accept=True)
            self.assertExpectedInline(
                r.stdout.replace(str(test_py), "test.py"),
                """\
Accepting new output at test.py:5
""",
            )
            r = sh(test_py)
            self.assertEqual(r.returncode, 0)

    def test_smoketest_accept_twice_reload(self) -> None:
        with smoketest("accept_twice_reload.py") as test_py:
            env = os.environ.copy()
            try:
                os.environ["EXPECTTEST_ACCEPT"] = "1"
                runpy.run_path(test_py)
                expecttest.EDIT_HISTORY.reload_file(test_py)
                try:
                    expecttest._TEST1 = True  # type: ignore[attr-defined]
                    runpy.run_path(test_py)
                finally:
                    delattr(expecttest, "_TEST1")
            finally:
                os.environ.clear()
                os.environ.update(env)

            # Should pass
            runpy.run_path(test_py)
            try:
                expecttest._TEST1 = True  # type: ignore[attr-defined]
                runpy.run_path(test_py)
            finally:
                delattr(expecttest, "_TEST1")

    def test_smoketest_accept_twice_clobber(self) -> None:
        with smoketest("accept_twice_clobber.py") as test_py:
            env = os.environ.copy()
            try:
                os.environ["EXPECTTEST_ACCEPT"] = "1"
                runpy.run_path(test_py)
                expecttest.EDIT_HISTORY.reload_file(test_py)
                try:
                    expecttest._TEST2 = True  # type: ignore[attr-defined]
                    self.assertRaises(AssertionError, lambda: runpy.run_path(test_py))
                finally:
                    delattr(expecttest, "_TEST2")
            finally:
                os.environ.clear()
                os.environ.update(env)

    def test_smoketest_expected_objects(self) -> None:
        with smoketest("accept_expected.py") as test_py:
            r = sh(test_py)
            self.assertNotEqual(r.returncode, 0)
            r = sh(test_py, accept=True)
            self.assertExpectedInline(
                r.stdout.replace(test_py, "test.py"),
                """\
Accepting new output at test.py:5
""",
            )
            r = sh(test_py)
            self.assertEqual(r.returncode, 0)


def load_tests(
    loader: unittest.TestLoader, tests: unittest.TestSuite, ignore: Any
) -> unittest.TestSuite:
    tests.addTests(doctest.DocTestSuite(expecttest))
    return tests


if __name__ == "__main__":
    unittest.main()
