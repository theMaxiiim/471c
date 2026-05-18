from L4.parse import parse_program, parse_term
from L4.syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Chan,
    Close,
    Closed,
    Immediate,
    Jump,
    Label,
    Let,
    LetRec,
    Load,
    Primitive,
    Program,
    Recv,
    Reference,
    Send,
    Spawn,
    Store,
)


# Let
def test_parse_let_empty():
    source = "(let () x)"

    expected = Let(
        bindings=[],
        body=Reference(name="x"),
    )

    actual = parse_term(source)

    assert actual == expected


def test_parse_let_bindings():
    source = "(let ((x 0)) x)"

    expected = Let(
        bindings=[
            ("x", Immediate(value=0)),
        ],
        body=Reference(name="x"),
    )

    actual = parse_term(source)

    assert actual == expected


# LetRec
def test_parse_letrec_empty():
    source = "(letrec () x)"

    expected = LetRec(
        bindings=[],
        body=Reference(name="x"),
    )

    actual = parse_term(source)

    assert actual == expected


def test_parse_letrec_bindings():
    source = "(letrec ((x 0)) x)"

    expected = LetRec(
        bindings=[
            ("x", Immediate(value=0)),
        ],
        body=Reference(name="x"),
    )

    actual = parse_term(source)

    assert actual == expected


# Reference
def test_parse_reference():
    source = "x"

    expected = Reference(
        name="x",
    )

    actual = parse_term(source)

    assert actual == expected


# Abstract
def test_parse_abstract():
    source = "(\\ (x) x)"

    expected = Abstract(
        parameters=["x"],
        body=Reference(name="x"),
    )

    actual = parse_term(source)

    assert actual == expected


# Apply
def test_parse_apply_empty():
    source = "(x)"

    expected = Apply(
        target=Reference(name="x"),
        arguments=[],
    )

    actual = parse_term(source)

    assert actual == expected


def test_parse_apply_arguments():
    source = "(x y z)"

    expected = Apply(
        target=Reference(name="x"),
        arguments=[Reference(name="y"), Reference(name="z")],
    )

    actual = parse_term(source)

    assert actual == expected


# Immediate
def test_parse_immediate():
    source = "42"

    expected = Immediate(value=42)

    actual = parse_term(source)

    assert actual == expected


# Primitive
def test_parse_add():
    source = "(+ 1 2)"

    expected = Primitive(
        operator="+",
        left=Immediate(value=1),
        right=Immediate(value=2),
    )

    actual = parse_term(source)

    assert actual == expected


def test_parse_subtract():
    source = "(- 3 2)"

    expected = Primitive(
        operator="-",
        left=Immediate(value=3),
        right=Immediate(value=2),
    )

    actual = parse_term(source)

    assert actual == expected


def test_parse_multiply():
    source = "(* 2 3)"
    expected = Primitive(
        operator="*",
        left=Immediate(value=2),
        right=Immediate(value=3),
    )
    actual = parse_term(source)
    assert actual == expected


# Branch
def test_parse_less_than():
    source = "(if (< 1 2) 1 0)"

    expected = Branch(
        operator="<",
        left=Immediate(value=1),
        right=Immediate(value=2),
        consequent=Immediate(value=1),
        otherwise=Immediate(value=0),
    )

    actual = parse_term(source)

    assert actual == expected


def test_parse_equal_to():
    source = "(if (== 1 1) 1 0)"

    expected = Branch(
        operator="==",
        left=Immediate(value=1),
        right=Immediate(value=1),
        consequent=Immediate(value=1),
        otherwise=Immediate(value=0),
    )

    actual = parse_term(source)

    assert actual == expected


# Allocate
def test_parse_allocate():
    source = "(allocate 0)"

    expected = Allocate(
        count=0,
    )

    actual = parse_term(source)

    assert actual == expected


# Load
def test_parse_load():
    source = "(load x 0)"

    expected = Load(
        base=Reference(name="x"),
        index=0,
    )

    actual = parse_term(source)

    assert actual == expected


# Store
def test_parse_store():
    source = "(store x 0 1)"

    expected = Store(
        base=Reference(name="x"),
        index=0,
        value=Immediate(value=1),
    )

    actual = parse_term(source)

    assert actual == expected


def test_parse_begin():
    source = "(begin x)"

    expected = Begin(
        effects=[],
        value=Reference(name="x"),
    )

    actual = parse_term(source)

    assert actual == expected


def test_parse_begin_effects():
    source = "(begin x y z)"

    expected = Begin(
        effects=[
            Reference(name="x"),
            Reference(name="y"),
        ],
        value=Reference(name="z"),
    )

    actual = parse_term(source)

    assert actual == expected


# Label
def test_parse_label():
    source = "(label done 42)"

    expected = Label(
        name="done",
        body=Immediate(value=42),
    )

    actual = parse_term(source)

    assert actual == expected


# Jump
def test_parse_jump():
    source = "(jump done 42)"

    expected = Jump(
        target=Reference(name="done"),
        value=Immediate(value=42),
    )

    actual = parse_term(source)

    assert actual == expected


# Chan
def test_parse_chan():
    source = "(chan)"
    expected = Chan()
    actual = parse_term(source)
    assert actual == expected


def test_parse_chan_buffered():
    source = "(chan 3)"
    expected = Chan(capacity=3)
    actual = parse_term(source)
    assert actual == expected


# Send
def test_parse_send():
    source = "(send ch 42)"

    expected = Send(
        channel=Reference(name="ch"),
        value=Immediate(value=42),
    )

    actual = parse_term(source)

    assert actual == expected


# Recv
def test_parse_recv():
    source = "(recv ch)"

    expected = Recv(
        channel=Reference(name="ch"),
    )

    actual = parse_term(source)

    assert actual == expected


# Spawn
def test_parse_spawn():
    source = "(spawn (\\ () (send ch 42)))"

    expected = Spawn(
        body=Abstract(
            parameters=[],
            body=Send(
                channel=Reference(name="ch"),
                value=Immediate(value=42),
            ),
        ),
    )

    actual = parse_term(source)

    assert actual == expected


# Close
def test_parse_close():
    source = "(close ch)"

    expected = Close(
        channel=Reference(name="ch"),
    )

    actual = parse_term(source)

    assert actual == expected


# Closed
def test_parse_closed():
    source = "(closed? ch)"

    expected = Closed(
        channel=Reference(name="ch"),
    )

    actual = parse_term(source)

    assert actual == expected


# Program
def test_parse_program_identity():
    source = "(l4 (x) x)"

    expected = Program(
        parameters=["x"],
        body=Reference(name="x"),
    )

    actual = parse_program(source)

    assert actual == expected


def test_parse_program_chan_send_recv():
    source = """(l4 ()
        (let ((ch (chan)))
            (begin
                (send ch 42)
                (recv ch))))"""

    expected = Program(
        parameters=[],
        body=Let(
            bindings=[("ch", Chan())],
            body=Begin(
                effects=[Send(channel=Reference(name="ch"), value=Immediate(value=42))],
                value=Recv(channel=Reference(name="ch")),
            ),
        ),
    )

    actual = parse_program(source)

    assert actual == expected


def test_parse_program_close_closed():
    source = """(l4 ()
        (let ((ch (chan)))
            (begin
                (close ch)
                (closed? ch))))"""

    expected = Program(
        parameters=[],
        body=Let(
            bindings=[("ch", Chan())],
            body=Begin(
                effects=[Close(channel=Reference(name="ch"))],
                value=Closed(channel=Reference(name="ch")),
            ),
        ),
    )

    actual = parse_program(source)

    assert actual == expected
