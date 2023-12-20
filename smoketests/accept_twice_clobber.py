import expecttest
from expecttest import assert_expected_inline

S1 = "a\nb"
S2 = "a\nb\nc"

assert_expected_inline(S2 if hasattr(expecttest, "_TEST2") else S1, """""")
