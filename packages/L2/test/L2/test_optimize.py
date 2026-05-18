import pytest
from L2.optimize import (
    free_variables,
    optimize_program,
    optimize_term,
    substitute,
)
from L2.syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Jump,
    Label,
    Let,
    Load,
    Primitive,
    Program,
    Reference,
    Store,
    Term,
)


def _prog(body: Term, params: list[str] | None = None) -> Program:
    return Program(parameters=params or [], body=body)


_X = Reference(name="x")
_A = Reference(name="a")
_P = Reference(name="p")
_F = Reference(name="f")


# -- free_variables --


def test_free_variables_all_cases():
    assert free_variables(Immediate(value=1)) == set()
    assert free_variables(Allocate(count=1)) == set()
    assert free_variables(Reference(name="x")) == {"x"}

    assert free_variables(
        Abstract(
            parameters=["x", "y"],
            body=Primitive(
                operator="+",
                left=Reference(name="x"),
                right=Reference(name="z"),
            ),
        )
    ) == {"z"}

    assert free_variables(
        Apply(
            target=Reference(name="f"),
            arguments=[
                Reference(name="x"),
                Primitive(
                    operator="+",
                    left=Reference(name="y"),
                    right=Immediate(value=1),
                ),
            ],
        )
    ) == {"f", "x", "y"}

    assert free_variables(Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y"))) == {"x", "y"}

    assert free_variables(
        Branch(
            operator="<",
            left=Reference(name="a"),
            right=Reference(name="b"),
            consequent=Reference(name="c"),
            otherwise=Reference(name="d"),
        )
    ) == {"a", "b", "c", "d"}

    assert free_variables(Load(base=Reference(name="arr"), index=0)) == {"arr"}
    assert free_variables(Store(base=Reference(name="arr"), index=0, value=Reference(name="val"))) == {"arr", "val"}

    assert free_variables(
        Begin(
            effects=[
                Reference(name="u"),
                Store(base=Reference(name="a"), index=0, value=Reference(name="b")),
            ],
            value=Reference(name="v"),
        )
    ) == {"u", "a", "b", "v"}

    assert free_variables(
        Let(
            bindings=[
                ("x", Reference(name="a")),
                ("y", Primitive(operator="+", left=Reference(name="x"), right=Reference(name="b"))),
            ],
            body=Primitive(operator="+", left=Reference(name="y"), right=Reference(name="c")),
        )
    ) == {"a", "b", "c"}


def test_free_variables_label():
    assert free_variables(Label(name="done", body=Reference(name="done"))) == set()
    assert free_variables(Label(name="done", body=Reference(name="x"))) == {"x"}
    assert free_variables(Label(name="k", body=Jump(target=Reference(name="k"), value=Reference(name="x")))) == {"x"}


def test_free_variables_jump():
    assert free_variables(Jump(target=Reference(name="k"), value=Reference(name="x"))) == {"k", "x"}


# -- substitute --

SUBSTITUTE_CASES: list[tuple[str, list[str], Term, Term]] = [
    ("reference_match", [], _X, Immediate(value=1)),
    ("reference_no_match", ["y"], Reference(name="y"), Reference(name="y")),
    ("immediate", [], Immediate(value=99), Immediate(value=99)),
    ("allocate", [], Allocate(count=3), Allocate(count=3)),
    (
        "abstract_no_shadow",
        [],
        Abstract(parameters=["y"], body=_X),
        Abstract(parameters=["y"], body=Immediate(value=1)),
    ),
    ("abstract_shadowed", [], Abstract(parameters=["x"], body=_X), Abstract(parameters=["x"], body=_X)),
    ("apply", ["f"], Apply(target=_F, arguments=[_X]), Apply(target=_F, arguments=[Immediate(value=1)])),
    (
        "primitive",
        [],
        Primitive(operator="+", left=_X, right=_X),
        Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1)),
    ),
    (
        "branch",
        ["a"],
        Branch(operator="<", left=_X, right=_A, consequent=_X, otherwise=_A),
        Branch(operator="<", left=Immediate(value=1), right=_A, consequent=Immediate(value=1), otherwise=_A),
    ),
    ("load", [], Load(base=_X, index=0), Load(base=Immediate(value=1), index=0)),
    ("store", ["p"], Store(base=_P, index=0, value=_X), Store(base=_P, index=0, value=Immediate(value=1))),
    ("begin", [], Begin(effects=[_X], value=_X), Begin(effects=[Immediate(value=1)], value=Immediate(value=1))),
    (
        "let_no_shadow",
        [],
        Let(bindings=[("y", _X)], body=Reference(name="y")),
        Let(bindings=[("y", Immediate(value=1))], body=Reference(name="y")),
    ),
    (
        "let_shadowed",
        [],
        Let(bindings=[("x", Immediate(value=9))], body=_X),
        Let(bindings=[("x", Immediate(value=9))], body=_X),
    ),
    ("label_no_shadow", [], Label(name="done", body=_X), Label(name="done", body=Immediate(value=1))),
    ("label_shadowed", [], Label(name="x", body=_X), Label(name="x", body=_X)),
    (
        "jump",
        ["k"],
        Jump(target=Reference(name="k"), value=_X),
        Jump(target=Reference(name="k"), value=Immediate(value=1)),
    ),
    (
        "let_shadowed_later_binding",
        ["f"],
        Let(bindings=[("x", Immediate(value=9)), ("y", Apply(target=_F, arguments=[_X]))], body=Reference(name="y")),
        Let(bindings=[("x", Immediate(value=9)), ("y", Apply(target=_F, arguments=[_X]))], body=Reference(name="y")),
    ),
]


@pytest.mark.parametrize(
    "name, extra_params, term, expected",
    SUBSTITUTE_CASES,
    ids=[c[0] for c in SUBSTITUTE_CASES],
)
def test_substitute_cases(name: str, extra_params: list[str], term: Term, expected: Term):
    actual = substitute(term, "x", Immediate(value=1))
    assert actual == expected


# -- optimize_term --


def test_optimize_term_main_paths():
    assert optimize_term(Reference(name="x")) == Reference(name="x")
    assert optimize_term(Immediate(value=1)) == Immediate(value=1)
    assert optimize_term(Allocate(count=2)) == Allocate(count=2)

    assert optimize_term(
        Abstract(
            parameters=["x"],
            body=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
        )
    ) == Abstract(parameters=["x"], body=Immediate(value=3))

    assert optimize_term(
        Apply(
            target=_F,
            arguments=[Primitive(operator="+", left=Immediate(value=2), right=Immediate(value=3))],
        )
    ) == Apply(target=_F, arguments=[Immediate(value=5)])

    # constant folding
    assert optimize_term(Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2))) == Immediate(
        value=3
    )
    assert optimize_term(Primitive(operator="-", left=Immediate(value=5), right=Immediate(value=2))) == Immediate(
        value=3
    )
    assert optimize_term(Primitive(operator="*", left=Immediate(value=4), right=Immediate(value=3))) == Immediate(
        value=12
    )
    non_fold_prim = Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=2))
    assert optimize_term(non_fold_prim) == non_fold_prim

    # branch folding
    assert optimize_term(
        Branch(
            operator="<",
            left=Immediate(value=1),
            right=Immediate(value=2),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
    ) == Immediate(value=10)
    assert optimize_term(
        Branch(
            operator="<",
            left=Immediate(value=2),
            right=Immediate(value=1),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
    ) == Immediate(value=20)
    assert optimize_term(
        Branch(
            operator="==",
            left=Immediate(value=2),
            right=Immediate(value=2),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
    ) == Immediate(value=10)
    assert optimize_term(
        Branch(
            operator="==",
            left=Immediate(value=2),
            right=Immediate(value=3),
            consequent=Immediate(value=10),
            otherwise=Immediate(value=20),
        )
    ) == Immediate(value=20)
    assert optimize_term(
        Branch(
            operator="<",
            left=Reference(name="x"),
            right=Immediate(value=0),
            consequent=Primitive(operator="*", left=Immediate(value=2), right=Immediate(value=3)),
            otherwise=Primitive(operator="-", left=Immediate(value=8), right=Immediate(value=1)),
        )
    ) == Branch(
        operator="<",
        left=Reference(name="x"),
        right=Immediate(value=0),
        consequent=Immediate(value=6),
        otherwise=Immediate(value=7),
    )

    # load / store recurse
    assert optimize_term(
        Load(base=Let(bindings=[("a", Immediate(value=1))], body=Reference(name="a")), index=0)
    ) == Load(base=Immediate(value=1), index=0)

    assert optimize_term(
        Store(
            base=Let(bindings=[("a", Immediate(value=1))], body=Reference(name="a")),
            index=0,
            value=Primitive(operator="+", left=Immediate(value=3), right=Immediate(value=4)),
        )
    ) == Store(base=Immediate(value=1), index=0, value=Immediate(value=7))

    # begin recurses
    assert optimize_term(
        Begin(
            effects=[
                Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
            ],
            value=Primitive(operator="*", left=Immediate(value=2), right=Immediate(value=3)),
        )
    ) == Begin(
        effects=[Immediate(value=3)],
        value=Immediate(value=6),
    )

    # single-pass let propagation
    assert optimize_term(
        Let(
            bindings=[
                ("x", Primitive(operator="+", left=Reference(name="a"), right=Immediate(value=1))),
                ("y", Reference(name="x")),
            ],
            body=Reference(name="y"),
        )
    ) == Let(
        bindings=[
            ("x", Primitive(operator="+", left=Reference(name="a"), right=Immediate(value=1))),
        ],
        body=Reference(name="x"),
    )


def test_optimize_term_label():
    assert optimize_term(
        Label(
            name="done",
            body=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
        )
    ) == Label(name="done", body=Immediate(value=3))


def test_optimize_term_jump():
    assert optimize_term(
        Jump(
            target=Reference(name="done"),
            value=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
        )
    ) == Jump(target=Reference(name="done"), value=Immediate(value=3))


def test_optimize_term_jump_target_recurses():
    assert optimize_term(
        Jump(
            target=Let(bindings=[("k", Reference(name="done"))], body=Reference(name="k")),
            value=Immediate(value=0),
        )
    ) == Jump(target=Reference(name="done"), value=Immediate(value=0))


# -- multi-step (optimize_program) --


def test_optimize_program_multi_step_propagation():
    assert optimize_program(
        _prog(
            Let(
                bindings=[
                    ("x", Immediate(value=5)),
                    ("y", Reference(name="x")),
                    ("z", Primitive(operator="+", left=Reference(name="y"), right=Immediate(value=1))),
                ],
                body=Reference(name="z"),
            )
        )
    ) == _prog(Immediate(value=6))


# -- label / jump via optimize_program --


def test_label_recurses():
    actual = optimize_program(
        _prog(
            Label(
                name="done",
                body=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
            )
        )
    )
    assert actual == _prog(Label(name="done", body=Immediate(value=3)))


def test_jump_recurses():
    actual = optimize_program(
        _prog(
            Label(
                name="done",
                body=Jump(
                    target=Reference(name="done"),
                    value=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
                ),
            )
        )
    )
    assert actual == _prog(
        Label(
            name="done",
            body=Jump(
                target=Reference(name="done"),
                value=Immediate(value=3),
            ),
        )
    )


def test_free_vars_label_dce():
    body = Let(
        bindings=[("x", Apply(target=_F, arguments=[]))],
        body=Label(name="done", body=_X),
    )
    assert optimize_program(_prog(body, ["f"])) == _prog(body, ["f"])


def test_free_vars_jump_dce():
    body = Let(
        bindings=[("x", Apply(target=_F, arguments=[]))],
        body=Label(name="k", body=Jump(target=Reference(name="k"), value=_X)),
    )
    assert optimize_program(_prog(body, ["f"])) == _prog(body, ["f"])


def test_dce_removes_unused_with_label():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("unused", Immediate(value=99))],
                body=Label(name="done", body=Immediate(value=0)),
            )
        )
    )
    assert actual == _prog(Label(name="done", body=Immediate(value=0)))


def test_substitute_label_no_shadow_optimize():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("x", Immediate(value=5))],
                body=Label(name="done", body=_X),
            )
        )
    )
    assert actual == _prog(Label(name="done", body=Immediate(value=5)))


def test_substitute_label_shadowed_optimize():
    actual = optimize_program(
        _prog(
            Let(
                bindings=[("done", Immediate(value=5))],
                body=Label(name="done", body=Reference(name="done")),
            )
        )
    )
    assert actual == _prog(Label(name="done", body=Reference(name="done")))


# -- optimize_program --


def test_optimize_program_fixed_point():
    assert optimize_program(
        Program(
            parameters=[],
            body=Let(
                bindings=[
                    ("x", Immediate(value=1)),
                    ("y", Reference(name="x")),
                    ("z", Primitive(operator="+", left=Reference(name="y"), right=Immediate(value=2))),
                ],
                body=Reference(name="z"),
            ),
        )
    ) == Program(parameters=[], body=Immediate(value=3))

    immediate_program = Program(parameters=[], body=Immediate(value=42))
    reference_program = Program(parameters=["x"], body=Reference(name="x"))
    allocate_program = Program(parameters=[], body=Allocate(count=4))
    assert optimize_program(immediate_program) == immediate_program
    assert optimize_program(reference_program) == reference_program
    assert optimize_program(allocate_program) == allocate_program


def test_optimize_term_dce_non_propagatable_dead():
    actual = optimize_term(
        Let(
            bindings=[("x", Primitive(operator="+", left=Reference(name="a"), right=Immediate(value=1)))],
            body=Immediate(value=0),
        )
    )
    assert actual == Immediate(value=0)


def test_optimize_term_dce_mixed_live_and_dead():
    actual = optimize_term(
        Let(
            bindings=[
                ("x", Primitive(operator="+", left=Reference(name="a"), right=Immediate(value=1))),
                ("y", Primitive(operator="*", left=Reference(name="a"), right=Immediate(value=2))),
            ],
            body=Reference(name="y"),
        )
    )
    assert actual == Let(
        bindings=[("y", Primitive(operator="*", left=Reference(name="a"), right=Immediate(value=2)))],
        body=Reference(name="y"),
    )


def test_optimize_term_let_propagate_rebinding():
    actual = optimize_term(
        Let(
            bindings=[
                ("x", Immediate(value=1)),
                ("x", Primitive(operator="+", left=Reference(name="a"), right=Immediate(value=2))),
            ],
            body=Reference(name="x"),
        )
    )
    assert actual == Let(
        bindings=[
            ("x", Primitive(operator="+", left=Reference(name="a"), right=Immediate(value=2))),
        ],
        body=Reference(name="x"),
    )
