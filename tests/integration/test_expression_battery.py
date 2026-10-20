import pytest
import mvp_server

BATTERY_CASES = [
    (1, "5+-1(3-1)/(9-3)", 14/3),
    (2, "2+3*4", 14),
    (3, "(2+3)*4", 20),
    (4, "10-4/2", 8),
    (5, "-5+8", 3),
    (6, "7--3", 10),
    (7, "2(3+4)", 14),
    (8, "2(3+4)(5-1)", 56),
    (9, "(1+2)(3+4)", 21),
    (10, "3(-2)", -6),
    (11, "12/(2+4)", 2),
    (12, "1/3+1/6", 0.5),
    (13, "2^3", 8),
    (14, "2^-2", 0.25),
    (15, "-2^2", -4),
    (16, "(-2)^2", 4),
    (17, "sqrt(16)", 4),
    (18, "sqrt(9+16)", 5),
    (19, "5!", 120),
    (20, "10/4", 2.5),
    (21, "0.1+0.2", 0.3),
    (22, "100*1.05^2", 110.25),
    (23, "(3-1)/(9-3)", 1/3),
    (24, "8/2(2+2)", 1),
    (25, "1/2+1/3", 5/6),
    (26, "3.5*2", 7),
    (27, "9-3*2+1", 4),
    (28, "sin(30)", 0.5),
    (29, "log(100)", 2),
    (30, "2*pi", 6.283185307179586),
    (32, "99999*99999", 9999800001),
    (33, "7+(-3)(-2)", 13),
    (34, "2*(3+(4-1)*2)", 18),
    (36, "1(3-1)", 2),
    (37, "(2)(3)", 6),
    (38, "2(3)(4)(5)", 120),
    (39, "-(3+4)", -7),
    (40, "3-(-2)", 5),
    (41, "(((1)))", 1),
    (42, "2*-3", -6),
    (43, "1+(2(3+4))", 15),
    (44, "(1+2)(3+4)(5+6)", 231),
    (45, "2(3+4)^2", 98),
    (46, "1/(1/(1/2))", 0.5),
]

@pytest.mark.parametrize("num,expr,expected", BATTERY_CASES)
def test_python_engine_battery(num, expr, expected):
    res = mvp_server.safe_evaluate_expression(expr, angle_unit="DEG")
    assert abs(res - expected) < 1e-7

def test_case_31_math_error():
    with pytest.raises((ValueError, ZeroDivisionError)):
        mvp_server.safe_evaluate_expression("(5+3)/(2-2)", angle_unit="DEG")

def test_case_35_ans_chaining():
    r1 = mvp_server.safe_evaluate_expression("5+5", angle_unit="DEG")
    r2 = mvp_server.safe_evaluate_expression(f"({r1})*2", angle_unit="DEG")
    assert r2 == 20

def test_sin_square_function_power():
    # 1 + sin(30)^2 = 1.25
    res = mvp_server.safe_evaluate_expression("1+(sin(30))^2", angle_unit="DEG")
    assert abs(res - 1.25) < 1e-7

def test_ans_chaining_in_engine():
    # 5+5 then = then *2 =
    r1 = mvp_server.safe_evaluate_expression("5+5", angle_unit="DEG")
    r2 = mvp_server.safe_evaluate_expression(f"({r1})*2", angle_unit="DEG")
    assert r2 == 20

def test_variant_unicode_minus():
    res = mvp_server.safe_evaluate_expression("5+−1(3-1)/(9-3)", angle_unit="DEG")
    assert abs(res - 14/3) < 1e-7

def test_variant_spaces_and_slash():
    res = mvp_server.safe_evaluate_expression("1 / 3 + 1 / 6", angle_unit="DEG")
    assert abs(res - 0.5) < 1e-7
