from L3 import syntax as L3
from L4 import syntax as L4
from L4.desugar import desugar_program, desugar_term


def test_desugar_immediate():
    assert desugar_term(L4.Immediate(value=42)) == L3.Immediate(value=42)


def test_desugar_reference():
    assert desugar_term(L4.Reference(name="x")) == L3.Reference(name="x")


def test_desugar_allocate():
    assert desugar_term(L4.Allocate(count=3)) == L3.Allocate(count=3)


def test_desugar_primitive():
    term = L4.Primitive(
        operator="+",
        left=L4.Immediate(value=1),
        right=L4.Immediate(value=2),
    )
    expected = L3.Primitive(
        operator="+",
        left=L3.Immediate(value=1),
        right=L3.Immediate(value=2),
    )
    assert desugar_term(term) == expected


def test_desugar_let():
    term = L4.Let(
        bindings=[("x", L4.Immediate(value=1))],
        body=L4.Reference(name="x"),
    )
    expected = L3.Let(
        bindings=[("x", L3.Immediate(value=1))],
        body=L3.Reference(name="x"),
    )
    assert desugar_term(term) == expected


def test_desugar_letrec():
    term = L4.LetRec(
        bindings=[("f", L4.Abstract(parameters=["x"], body=L4.Reference(name="x")))],
        body=L4.Reference(name="f"),
    )
    expected = L3.LetRec(
        bindings=[("f", L3.Abstract(parameters=["x"], body=L3.Reference(name="x")))],
        body=L3.Reference(name="f"),
    )
    assert desugar_term(term) == expected


def test_desugar_abstract():
    term = L4.Abstract(parameters=["x"], body=L4.Reference(name="x"))
    expected = L3.Abstract(parameters=["x"], body=L3.Reference(name="x"))
    assert desugar_term(term) == expected


def test_desugar_apply():
    term = L4.Apply(
        target=L4.Reference(name="f"),
        arguments=[L4.Immediate(value=1)],
    )
    expected = L3.Apply(
        target=L3.Reference(name="f"),
        arguments=[L3.Immediate(value=1)],
    )
    assert desugar_term(term) == expected


def test_desugar_branch():
    term = L4.Branch(
        operator="<",
        left=L4.Immediate(value=1),
        right=L4.Immediate(value=2),
        consequent=L4.Immediate(value=10),
        otherwise=L4.Immediate(value=20),
    )
    expected = L3.Branch(
        operator="<",
        left=L3.Immediate(value=1),
        right=L3.Immediate(value=2),
        consequent=L3.Immediate(value=10),
        otherwise=L3.Immediate(value=20),
    )
    assert desugar_term(term) == expected


def test_desugar_load():
    term = L4.Load(base=L4.Reference(name="x"), index=0)
    expected = L3.Load(base=L3.Reference(name="x"), index=0)
    assert desugar_term(term) == expected


def test_desugar_store():
    term = L4.Store(base=L4.Reference(name="x"), index=0, value=L4.Immediate(value=1))
    expected = L3.Store(base=L3.Reference(name="x"), index=0, value=L3.Immediate(value=1))
    assert desugar_term(term) == expected


def test_desugar_begin():
    term = L4.Begin(effects=[L4.Immediate(value=1)], value=L4.Immediate(value=2))
    expected = L3.Begin(effects=[L3.Immediate(value=1)], value=L3.Immediate(value=2))
    assert desugar_term(term) == expected


def test_desugar_label():
    term = L4.Label(name="done", body=L4.Immediate(value=42))
    expected = L3.Label(name="done", body=L3.Immediate(value=42))
    assert desugar_term(term) == expected


def test_desugar_jump():
    term = L4.Jump(target=L4.Reference(name="k"), value=L4.Immediate(value=0))
    expected = L3.Jump(target=L3.Reference(name="k"), value=L3.Immediate(value=0))
    assert desugar_term(term) == expected


def test_desugar_chan():
    result = desugar_term(L4.Chan())
    assert isinstance(result, L3.Let)
    assert result.bindings[0][1] == L3.Allocate(count=4)


# -- send --


def test_desugar_send():
    result = desugar_term(L4.Send(channel=L4.Reference(name="ch"), value=L4.Immediate(value=42)))
    assert isinstance(result, L3.Let)
    bindings = dict(result.bindings)
    assert bindings["__sch"] == L3.Reference(name="ch")
    assert bindings["__sv"] == L3.Immediate(value=42)
    assert isinstance(result.body, L3.Branch)


def test_desugar_recv():
    result = desugar_term(L4.Recv(channel=L4.Reference(name="ch")))
    assert isinstance(result, L3.Let)
    bindings = dict(result.bindings)
    assert bindings["__rch"] == L3.Reference(name="ch")
    assert isinstance(result.body, L3.Branch)


# -- spawn --


def test_desugar_spawn():
    result = desugar_term(L4.Spawn(body=L4.Abstract(parameters=[], body=L4.Immediate(value=0))))
    assert isinstance(result, L3.Label)
    assert result.name == "__k_parent"


# --close--


def test_desugar_close():
    result = desugar_term(L4.Close(channel=L4.Reference(name="ch")))
    assert isinstance(result, L3.Let)
    bindings = dict(result.bindings)
    assert bindings["__cch"] == L3.Reference(name="ch")
    assert isinstance(result.body, L3.Branch)


def test_desugar_closed():
    result = desugar_term(L4.Closed(channel=L4.Reference(name="ch")))
    assert isinstance(result, L3.Let)
    bindings = dict(result.bindings)
    assert bindings["__clch"] == L3.Reference(name="ch")
    assert isinstance(result.body, L3.Load)
    assert result.body.index == 3


def test_desugar_program():
    program = L4.Program(
        parameters=["x"],
        body=L4.Reference(name="x"),
    )
    result = desugar_program(program)
    assert isinstance(result, L3.Program)
    assert result.parameters == ["x"]
    assert isinstance(result.body, L3.Let)
    bindings = dict(result.body.bindings)
    assert bindings["__rq"] == L3.Allocate(count=1)
