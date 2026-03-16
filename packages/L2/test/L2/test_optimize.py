import pytest
from L2.optimize import optimize_program
from L2.syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    Load,
    Primitive,
    Program,
    Reference,
    Store,
)


def _prog(body, params=None):
    return Program(parameters=params or [], body=body)


@pytest.mark.parametrize(
    "op, a, b, expected",
    [
        ("+", 2, 3, 5),
        ("-", 7, 4, 3),
        ("*", 3, 5, 15),
    ],
)
def test_fold_primitive(op, a, b, expected):
    actual = optimize_program(_prog(Primitive(operator=op, left=Immediate(value=a), right=Immediate(value=b))))
    assert actual == _prog(Immediate(value=expected))


def test_no_fold_primitive_non_constant():
    body = Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=1))
    assert optimize_program(_prog(body, ["x"])) == _prog(body, ["x"])


## constant folding


@pytest.mark.parametrize(
    "op, a, b, picks_consequent",
    [
        ("<", 1, 5, True),
        ("<", 5, 1, False),
        ("==", 3, 3, True),
        ("==", 3, 4, False),
    ],
)
def test_fold_branch(op, a, b, picks_consequent):
    actual = optimize_program(
        _prog(
            Branch(
                operator=op,
                left=Immediate(value=a),
                right=Immediate(value=b),
                consequent=Immediate(value=10),
                otherwise=Immediate(value=20),
            )
        )
    )
    assert actual == _prog(Immediate(value=10 if picks_consequent else 20))


def test_no_fold_branch_non_constant():
    body = Branch(
        operator="<",
        left=Reference(name="x"),
        right=Immediate(value=5),
        consequent=Immediate(value=10),
        otherwise=Immediate(value=20),
    )
    assert optimize_program(_prog(body, ["x"])) == _prog(body, ["x"])


def test_branch_fold_optimizes_chosen_arm():
    actual = optimize_program(
        _prog(
            Branch(
                operator="==",
                left=Immediate(value=1),
                right=Immediate(value=1),
                consequent=Primitive(operator="+", left=Immediate(value=2), right=Immediate(value=3)),
                otherwise=Immediate(value=0),
            )
        )
    )
    assert actual == _prog(Immediate(value=5))


# ===== Constant Propagation =====


def test_propagate_immediate():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("x", Immediate(value=7))],
                body=Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=1)),
            )
        )
    )
    assert actual == _prog(Immediate(value=8))


def test_propagate_reference():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("x", Reference(name="y"))],
                body=Reference(name="x"),
            ),
            ["y"],
        )
    )
    assert actual == _prog(Reference(name="y"), ["y"])


def test_propagate_chain():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("x", Immediate(value=3)), ("y", Reference(name="x"))],
                body=Reference(name="y"),
            )
        )
    )
    assert actual == _prog(Immediate(value=3))


def test_propagate_into_later_bindings():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[
                    ("x", Immediate(value=2)),
                    ("y", Primitive(operator="+", left=Reference(name="x"), right=Reference(name="a"))),
                ],
                body=Reference(name="y"),
            ),
            ["a"],
        )
    )
    assert actual == _prog(
        Let(
            bindings=[("y", Primitive(operator="+", left=Immediate(value=2), right=Reference(name="a")))],
            body=Reference(name="y"),
        ),
        ["a"],
    )


_X = Reference(name="x")
_A = Reference(name="a")
_P = Reference(name="p")
_F = Reference(name="f")

SUBSTITUTE_CASES = [
    ("reference", [], _X, Immediate(value=1)),
    ("reference_no_match", ["y"], Reference(name="y"), Reference(name="y")),
    ("primitive", [], Primitive(operator="+", left=_X, right=_X), Immediate(value=2)),
    ("apply", ["f"], Apply(target=_F, arguments=[_X]), Apply(target=_F, arguments=[Immediate(value=1)])),
    (
        "branch",
        ["a"],
        Branch(operator="<", left=_X, right=_A, consequent=_X, otherwise=_A),
        Branch(operator="<", left=Immediate(value=1), right=_A, consequent=Immediate(value=1), otherwise=_A),
    ),
    ("load", [], Load(base=_X, index=0), Load(base=Immediate(value=1), index=0)),
    ("store", ["p"], Store(base=_P, index=0, value=_X), Store(base=_P, index=0, value=Immediate(value=1))),
    (
        "begin",
        ["p"],
        Begin(effects=[Store(base=_P, index=0, value=_X)], value=_X),
        Begin(effects=[Store(base=_P, index=0, value=Immediate(value=1))], value=Immediate(value=1)),
    ),
    (
        "abstract_no_shadow",
        [],
        Abstract(parameters=["y"], body=_X),
        Abstract(parameters=["y"], body=Immediate(value=1)),
    ),
    ("abstract_shadowed", [], Abstract(parameters=["x"], body=_X), Abstract(parameters=["x"], body=_X)),
    ("nested_let_no_shadow", [], Let(bindings=[("y", _X)], body=Reference(name="y")), Immediate(value=1)),
    ("nested_let_shadowed", [], Let(bindings=[("x", Immediate(value=9))], body=_X), Immediate(value=9)),
    ("immediate", [], Immediate(value=99), Immediate(value=99)),
    ("allocate", [], Allocate(count=3), Allocate(count=3)),
]


@pytest.mark.parametrize(
    "name, extra_params, body, expected_body", SUBSTITUTE_CASES, ids=[c[0] for c in SUBSTITUTE_CASES]
)
def test_propagate_through(name, extra_params, body, expected_body):
    actual = optimize_program(
        _prog(
            Let(bindings=[("x", Immediate(value=1))], body=body),
            extra_params,
        )
    )
    assert actual == _prog(expected_body, extra_params)


FREE_VAR_CASES = [
    ("reference", ["v"], Reference(name="v")),
    ("immediate", [], Immediate(value=42)),
    ("allocate", [], Allocate(count=2)),
    ("abstract", ["a"], Abstract(parameters=["x"], body=_A)),
    ("apply", ["f", "a"], Apply(target=_F, arguments=[_A])),
    ("primitive", ["a"], Primitive(operator="+", left=_A, right=Immediate(value=1))),
    (
        "branch",
        ["a", "b"],
        Branch(
            operator="<",
            left=_A,
            right=Reference(name="b"),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=2),
        ),
    ),
    ("load", ["p"], Load(base=_P, index=0)),
    ("store", ["p", "v"], Store(base=_P, index=0, value=Reference(name="v"))),
    ("begin", ["p", "v"], Begin(effects=[_P], value=Reference(name="v"))),
    ("let", ["a"], Let(bindings=[("y", _A)], body=Reference(name="y"))),
]


@pytest.mark.parametrize("name, params, body", FREE_VAR_CASES, ids=[c[0] for c in FREE_VAR_CASES])
def test_dce_removes_unused(name, params, body):
    program = _prog(Let(bindings=[("unused", Immediate(value=1))], body=body), params)
    actual = optimize_program(program)

    if name == "let":
        assert actual == _prog(_A, params)
    else:
        assert actual == _prog(body, params)


def test_dce_keeps_used_binding():
    body = Let(
        bindings=[("x", Primitive(operator="+", left=_A, right=Reference(name="b")))],
        body=_X,
    )
    assert optimize_program(_prog(body, ["a", "b"])) == _prog(body, ["a", "b"])


def test_dce_transitive_liveness():
    body = Let(
        bindings=[
            ("x", Primitive(operator="+", left=_A, right=Immediate(value=1))),
            ("y", Primitive(operator="*", left=_X, right=Immediate(value=2))),
        ],
        body=Reference(name="y"),
    )
    assert optimize_program(_prog(body, ["a"])) == _prog(body, ["a"])


def test_dce_all_bindings_removed():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("x", Immediate(value=42))],
                body=Immediate(value=0),
            )
        )
    )
    assert actual == _prog(Immediate(value=0))


def test_let_mixed_propagate_and_keep():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[
                    ("x", Immediate(value=1)),
                    ("y", Primitive(operator="+", left=_A, right=Immediate(value=2))),
                ],
                body=Primitive(operator="+", left=Reference(name="y"), right=_X),
            ),
            ["a"],
        )
    )
    assert actual == _prog(
        Let(
            bindings=[("y", Primitive(operator="+", left=_A, right=Immediate(value=2)))],
            body=Primitive(operator="+", left=Reference(name="y"), right=Immediate(value=1)),
        ),
        ["a"],
    )


def test_let_propagate_shadow_in_bindings():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("x", Immediate(value=1)), ("x", Immediate(value=2))],
                body=_X,
            )
        )
    )
    assert actual == _prog(Immediate(value=2))


def test_fixed_point_propagate_then_fold():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("x", Immediate(value=2))],
                body=Primitive(operator="*", left=_X, right=Immediate(value=3)),
            )
        )
    )
    assert actual == _prog(Immediate(value=6))


# ===== Structural recursion pass-through =====


def test_abstract_recurses():
    actual = optimize_program(
        _prog(
            Abstract(
                parameters=["a"],
                body=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
            )
        )
    )
    assert actual == _prog(Abstract(parameters=["a"], body=Immediate(value=3)))


def test_apply_recurses():
    actual = optimize_program(
        _prog(
            Apply(
                target=_F,
                arguments=[Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2))],
            ),
            ["f"],
        )
    )
    assert actual == _prog(Apply(target=_F, arguments=[Immediate(value=3)]), ["f"])


def test_load_recurses():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("x", Immediate(value=5))],
                body=Load(base=_X, index=0),
            )
        )
    )
    assert actual == _prog(Load(base=Immediate(value=5), index=0))


def test_store_recurses():
    actual = optimize_program(
        _prog(
            Store(
                base=_P,
                index=0,
                value=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1)),
            ),
            ["p"],
        )
    )
    assert actual == _prog(Store(base=_P, index=0, value=Immediate(value=2)), ["p"])


def test_begin_recurses():
    actual = optimize_program(
        _prog(
            Begin(
                effects=[
                    Store(
                        base=_P,
                        index=0,
                        value=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1)),
                    )
                ],
                value=Primitive(operator="*", left=Immediate(value=2), right=Immediate(value=3)),
            ),
            ["p"],
        )
    )
    assert actual == _prog(
        Begin(
            effects=[Store(base=_P, index=0, value=Immediate(value=2))],
            value=Immediate(value=6),
        ),
        ["p"],
    )
