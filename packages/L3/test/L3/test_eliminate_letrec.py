from L2 import syntax as L2
from L3 import syntax as L3
from L3.eliminate_letrec import eliminate_letrec_program, eliminate_letrec_term


def test_eliminate_letrec_term_immediate():
    result = eliminate_letrec_term(L3.Immediate(value=0), {})
    assert result == L2.Immediate(value=0)


def test_eliminate_letrec_term_reference():
    result = eliminate_letrec_term(L3.Reference(name="x"), {"x": False})
    assert result == L2.Reference(name="x")


def test_eliminate_letrec_term_reference_letrec_bound():
    result = eliminate_letrec_term(L3.Reference(name="x"), {"x": True})
    assert result == L2.Load(base=L2.Reference(name="x"), index=0)


def test_eliminate_letrec_term_primitive():
    term = L3.Primitive(operator="+", left=L3.Immediate(value=1), right=L3.Immediate(value=2))
    result = eliminate_letrec_term(term, {})
    assert result == L2.Primitive(operator="+", left=L2.Immediate(value=1), right=L2.Immediate(value=2))


def test_eliminate_letrec_term_branch():
    term = L3.Branch(
        operator="<",
        left=L3.Immediate(value=1),
        right=L3.Immediate(value=2),
        consequent=L3.Immediate(value=0),
        otherwise=L3.Immediate(value=1),
    )
    result = eliminate_letrec_term(term, {})
    assert result == L2.Branch(
        operator="<",
        left=L2.Immediate(value=1),
        right=L2.Immediate(value=2),
        consequent=L2.Immediate(value=0),
        otherwise=L2.Immediate(value=1),
    )


def test_eliminate_letrec_term_allocate():
    result = eliminate_letrec_term(L3.Allocate(count=3), {})
    assert result == L2.Allocate(count=3)


def test_eliminate_letrec_term_load():
    term = L3.Load(base=L3.Reference(name="x"), index=0)
    result = eliminate_letrec_term(term, {"x": False})
    assert result == L2.Load(base=L2.Reference(name="x"), index=0)


def test_eliminate_letrec_term_store():
    term = L3.Store(base=L3.Reference(name="x"), index=0, value=L3.Immediate(value=1))
    result = eliminate_letrec_term(term, {"x": False})
    assert result == L2.Store(base=L2.Reference(name="x"), index=0, value=L2.Immediate(value=1))


def test_eliminate_letrec_term_begin():
    term = L3.Begin(effects=[L3.Immediate(value=0)], value=L3.Immediate(value=1))
    result = eliminate_letrec_term(term, {})
    assert result == L2.Begin(effects=[L2.Immediate(value=0)], value=L2.Immediate(value=1))


def test_eliminate_letrec_term_apply():
    term = L3.Apply(target=L3.Reference(name="f"), arguments=[L3.Immediate(value=0)])
    result = eliminate_letrec_term(term, {"f": False})
    assert result == L2.Apply(target=L2.Reference(name="f"), arguments=[L2.Immediate(value=0)])


def test_eliminate_letrec_term_abstract():
    term = L3.Abstract(parameters=["x"], body=L3.Immediate(value=0))
    result = eliminate_letrec_term(term, {})
    assert result == L2.Abstract(parameters=["x"], body=L2.Immediate(value=0))


def test_eliminate_letrec_term_abstract_shadows_letrec():
    term = L3.Abstract(parameters=["x"], body=L3.Reference(name="x"))
    result = eliminate_letrec_term(term, {"x": True})
    assert result == L2.Abstract(parameters=["x"], body=L2.Reference(name="x"))


def test_eliminate_letrec_term_let():
    term = L3.Let(
        bindings=[("x", L3.Immediate(value=0))],
        body=L3.Reference(name="x"),
    )
    result = eliminate_letrec_term(term, {})
    assert result == L2.Let(
        bindings=[("x", L2.Immediate(value=0))],
        body=L2.Reference(name="x"),
    )


def test_eliminate_letrec_term_let_shadows_letrec():
    term = L3.Let(
        bindings=[("x", L3.Immediate(value=0))],
        body=L3.Reference(name="x"),
    )
    result = eliminate_letrec_term(term, {"x": True})
    assert result == L2.Let(
        bindings=[("x", L2.Immediate(value=0))],
        body=L2.Reference(name="x"),
    )


def test_eliminate_letrec_term_letrec():
    term = L3.LetRec(
        bindings=[
            (
                "f",
                L3.Abstract(
                    parameters=["x"], body=L3.Apply(target=L3.Reference(name="f"), arguments=[L3.Reference(name="x")])
                ),
            )
        ],
        body=L3.Reference(name="f"),
    )
    result = eliminate_letrec_term(term, {})
    assert result == L2.Let(
        bindings=[("f", L2.Allocate(count=1))],
        body=L2.Begin(
            effects=[
                L2.Store(
                    base=L2.Reference(name="f"),
                    index=0,
                    value=L2.Abstract(
                        parameters=["x"],
                        body=L2.Apply(
                            target=L2.Load(base=L2.Reference(name="f"), index=0),
                            arguments=[L2.Reference(name="x")],
                        ),
                    ),
                )
            ],
            value=L2.Load(base=L2.Reference(name="f"), index=0),
        ),
    )


def test_eliminate_letrec_program():
    program = L3.Program(parameters=[], body=L3.Immediate(value=0))
    result = eliminate_letrec_program(program)
    assert result == L2.Program(parameters=[], body=L2.Immediate(value=0))
