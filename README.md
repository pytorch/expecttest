# expecttest

This library implements expect tests (also known as "golden" tests). Expect
tests are a method of writing tests where instead of hard-coding the expected
output of a test, you instead run the test to get the output, and the test
framework automatically populates the expected output.  If the output of the
test changes, you can rerun the test with `EXPECTTEST_ACCEPT=1` environment
variable to automatically update the expected output.

Somewhat unusually, this file implements *inline* expect tests: that is to say,
the expected output isn't save to an external file, it is saved directly in the
Python file (and we modify your Python the file when updating the expect test.)

The general recipe for how to use this is as follows:

  1. Write your test and use `assertExpectedInline()` instead of a normal
     assertEqual.  Leave the expected argument blank with an empty string:
     ```py
     self.assertExpectedInline(some_func(), "")
     ```

  2. Run your test.  It should fail, and you get an error message about
     accepting the output with `EXPECTTEST_ACCEPT=1`

  3. Rerun the test with `EXPECTTEST_ACCEPT=1`.  Now the previously blank string
     literal will now contain the expected value of the test.
     ```py
     self.assertExpectedInline(some_func(), "my_value")
     ```

Some tips and tricks:

  - Often, you will want to expect test on a multiline string.  This framework
    understands triple-quoted strings, so you can just write `"""my_value"""`
    and it will turn into triple-quoted strings.

  - Take some time thinking about how exactly you want to design the output
    format of the expect test.  It is often profitable to design an output
    representation specifically for expect tests.
