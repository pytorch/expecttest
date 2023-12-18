import expecttest
import unittest

S1 = "a\nb"
S2 = "c\nd"


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
