import expecttest
import unittest

S1 = "你好，世界！"
S2 = "（the parentheses are in chinese）"


class Test(expecttest.TestCase):
    def bar(self):
        self.assertExpectedInline(
            S1,
            """\
w""",
        )

    def test_a(self):
        self.bar()
        self.bar()

    def test_b(self):
        self.assertExpectedInline(
            S2,
            """\
x
y
z""",
        )


if __name__ == "__main__":
    unittest.main()
