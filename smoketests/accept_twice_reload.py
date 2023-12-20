import expecttest
from expecttest import assert_expected_inline

S1 = "a\nb"
S2 = "a\nb\nc"

if hasattr(expecttest, "_TEST1"):
    assert_expected_inline(S1, """""")
else:
    assert_expected_inline(S2, """""")
