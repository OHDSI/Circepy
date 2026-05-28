"""Test parameter rendering - ported from OHDSI SqlRender test-renderSql.R"""

import warnings

import pytest

from circe.sqlrender import render


class TestRender:
    S = "{DEFAULT @a = '123'} SELECT * FROM table WHERE x = @a AND {@b == 'blaat'}?{y = 1234}:{x = 1};"

    def test_parameter_substitution(self):
        sql = render(self.S, a="abc")
        assert sql == " SELECT * FROM table WHERE x = abc AND x = 1;"

    def test_empty_parameter(self):
        sql = render(self.S, a="abc", b="")
        assert sql == " SELECT * FROM table WHERE x = abc AND x = 1;"

    def test_default(self):
        sql = render(self.S, b="1")
        assert sql == " SELECT * FROM table WHERE x = 123 AND x = 1;"

    def test_if_then_else_then(self):
        sql = render(self.S, b="blaat")
        assert sql == " SELECT * FROM table WHERE x = 123 AND y = 1234;"

    def test_if_then_else_else(self):
        sql = render(self.S, b="bla")
        assert sql == " SELECT * FROM table WHERE x = 123 AND x = 1;"

    def test_boolean_param_true(self):
        sql = render("SELECT * FROM table {@a}?{WHERE x = 1}", a=True)
        assert sql == "SELECT * FROM table WHERE x = 1"

    def test_boolean_param_false(self):
        sql = render("SELECT * FROM table {@a}?{WHERE x = 1}", a=False)
        assert sql == "SELECT * FROM table "

    def test_in_pattern_true(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sql = render("{1 IN (@a)}?{SELECT * FROM table}", a=[1, 2, 3, 4])
            assert sql == "SELECT * FROM table"

    def test_in_pattern_false(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sql = render("{1 IN (@a)}?{SELECT * FROM table}", a=[2, 3, 4])
            assert sql == ""

    def test_in_pattern_space_start_true(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sql = render("{ 1 IN (@a)}?{SELECT * FROM table}", a=[1, 2, 3, 4])
            assert sql == "SELECT * FROM table"

    def test_in_pattern_space_start_false(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sql = render("{ 1 IN (@a)}?{SELECT * FROM table}", a=[2, 3, 4])
            assert sql == ""

    def test_and_operator_true(self):
        sql = render("{true & true}?{true}:{false}")
        assert sql == "true"

    def test_and_operator_false(self):
        sql = render("{true & false}?{true}:{false}")
        assert sql == "false"

    def test_or_operator_true_1(self):
        sql = render("{true | false}?{true}:{false}")
        assert sql == "true"

    def test_or_operator_true_2(self):
        sql = render("{true | true}?{true}:{false}")
        assert sql == "true"

    def test_or_operator_false(self):
        sql = render("{false | false}?{true}:{false}")
        assert sql == "false"

    def test_nested_in_boolean(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sql = render("{true & (true & (true & 4 IN (@a)))}?{true}:{false}", a=[1, 2, 3])
            assert sql == "false"

    def test_nested_if_then_else_true(self):
        sql = render("{true}?{{true}?{double true}:{true false}}:{false}")
        assert sql == "double true"

    def test_nested_if_then_else_false(self):
        sql = render("{false}?{{true}?{double true}:{true false}}:{false}")
        assert sql == "false"

    def test_simple_negation(self):
        sql = render("{!false}?{true}:{false}")
        assert sql == "true"

    def test_negation_of_param(self):
        sql = render("{!@a}?{true}:{false}", a="true")
        assert sql == "false"

    def test_not_equals_operator_1(self):
        sql = render("{123 != 123}?{true}:{false}")
        assert sql == "false"

    def test_not_equals_operator_2(self):
        sql = render("{123 != 234}?{true}:{false}")
        assert sql == "true"

    def test_not_equals_operator_3(self):
        sql = render("{123 <> 123}?{true}:{false}")
        assert sql == "false"

    def test_not_equals_operator_4(self):
        sql = render("{123 <> 234}?{true}:{false}")
        assert sql == "true"

    def test_nested_in_evaluates_true(self):
        sql = render("{TRUE & (FALSE | 1 IN (1,2,3))}?{true}:{false}")
        assert sql == "true"

    def test_nested_in_evaluates_false(self):
        sql = render("{TRUE & (FALSE | 4 IN (1,2,3))}?{true}:{false}")
        assert sql == "false"

    def test_backslash_in_parameter(self):
        sql = render("SELECT * FROM table WHERE name = '@name';", name="NA\\joe")
        assert sql == "SELECT * FROM table WHERE name = 'NA\\joe';"

    def test_dollar_in_parameter(self):
        sql = render("SELECT * FROM table WHERE name = '@name';", name="NA$joe")
        assert sql == "SELECT * FROM table WHERE name = 'NA$joe';"

    def test_error_on_bad_boolean_syntax(self):
        from circe.sqlrender.renderer import SqlRenderError

        with pytest.raises(SqlRenderError):
            render("{true = true}?{true}:{false}")

    def test_warning_on_parameter_name_mismatch(self):
        with pytest.warns(UserWarning):
            render("SELECT * FROM @my_table", a_table="x")

    def test_no_problem_missing_parameters(self):
        assert render("SELECT * FROM @my_table") == "SELECT * FROM @my_table"

    def test_warning_on_old_function(self):
        with pytest.warns(UserWarning):
            render("SELECT * FROM @my_table", x="y")

    def test_inline_simple(self):
        sql = render("{1 == 1}?{yes}:{no}")
        assert sql == "yes"

    def test_inline_false(self):
        sql = render("{1 == 2}?{yes}:{no}")
        assert sql == "no"

    def test_inline_no_else(self):
        sql = render("{false}?{hide}")
        assert sql == ""
