from L3.syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    LetRec,
    Load,
    Primitive,
    Reference,
    Store,
)
from L3.uniqify import Context, Program, uniqify_program, uniqify_term
from util.sequential_name_generator import SequentialNameGenerator


def test_uniqify_term_reference():
    term = Reference(name="x")

    context: Context = {"x": "y"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh=fresh)

    expected = Reference(name="y")

    assert actual == expected


def test_uniqify_immediate():
    term = Immediate(value=42)

    context: Context = dict[str, str]()
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Immediate(value=42)

    assert actual == expected


def test_uniqify_term_let():
    term = Let(
        bindings=[
            ("x", Immediate(value=1)),
            ("y", Reference(name="x")),
        ],
        body=Apply(
            target=Reference(name="x"),
            arguments=[
                Reference(name="y"),
            ],
        ),
    )

    context: Context = {"x": "y"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Let(
        bindings=[
            ("x0", Immediate(value=1)),
            ("y0", Reference(name="y")),
        ],
        body=Apply(
            target=Reference(name="x0"),
            arguments=[
                Reference(name="y0"),
            ],
        ),
    )

    assert actual == expected


def test_uniqify_term_letrec():
    term = LetRec(
        bindings=[
            ("f", Abstract(parameters=["x"], body=Apply(target=Reference(name="g"), arguments=[Reference(name="x")]))),
            ("g", Abstract(parameters=["x"], body=Apply(target=Reference(name="f"), arguments=[Reference(name="x")]))),
        ],
        body=Apply(target=Reference(name="f"), arguments=[Immediate(value=1)]),
    )

    context: Context = dict[str, str]()
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = LetRec(
        bindings=[
            (
                "f0",
                Abstract(parameters=["x0"], body=Apply(target=Reference(name="g0"), arguments=[Reference(name="x0")])),
            ),
            (
                "g0",
                Abstract(parameters=["x1"], body=Apply(target=Reference(name="f0"), arguments=[Reference(name="x1")])),
            ),
        ],
        body=Apply(target=Reference(name="f0"), arguments=[Immediate(value=1)]),
    )

    assert actual == expected


def test_uniqify_term_abstract():
    term = Abstract(
        parameters=["x", "y"],
        body=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
    )

    context: Context = dict[str, str]()
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Abstract(
        parameters=["x0", "y0"],
        body=Primitive(operator="+", left=Reference(name="x0"), right=Reference(name="y0")),
    )

    assert actual == expected


def test_uniqify_term_apply():
    term = Apply(
        target=Reference(name="f"),
        arguments=[Reference(name="x"), Reference(name="y")],
    )

    context: Context = {"f": "f0", "x": "x0", "y": "y0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Apply(
        target=Reference(name="f0"),
        arguments=[Reference(name="x0"), Reference(name="y0")],
    )

    assert actual == expected


def test_uniqify_term_primitive():
    term = Primitive(
        operator="*",
        left=Reference(name="x"),
        right=Immediate(value=2),
    )

    context: Context = {"x": "x0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Primitive(
        operator="*",
        left=Reference(name="x0"),
        right=Immediate(value=2),
    )

    assert actual == expected


def test_uniqify_term_branch():
    term = Branch(
        operator="<",
        left=Reference(name="x"),
        right=Immediate(value=0),
        consequent=Immediate(value=1),
        otherwise=Reference(name="y"),
    )

    context: Context = {"x": "x0", "y": "y0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Branch(
        operator="<",
        left=Reference(name="x0"),
        right=Immediate(value=0),
        consequent=Immediate(value=1),
        otherwise=Reference(name="y0"),
    )

    assert actual == expected


def test_uniqify_term_allocate():
    term = Allocate(count=3)

    context: Context = dict[str, str]()
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Allocate(count=3)

    assert actual == expected


def test_uniqify_term_load():
    term = Load(
        base=Reference(name="arr"),
        index=0,
    )

    context: Context = {"arr": "arr0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Load(
        base=Reference(name="arr0"),
        index=0,
    )

    assert actual == expected


def test_uniqify_term_store():
    term = Store(
        base=Reference(name="arr"),
        index=0,
        value=Reference(name="v"),
    )

    context: Context = {"arr": "arr0", "v": "v0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Store(
        base=Reference(name="arr0"),
        index=0,
        value=Reference(name="v0"),
    )

    assert actual == expected


def test_uniqify_term_begin():
    term = Begin(
        effects=[
            Store(base=Reference(name="arr"), index=0, value=Immediate(value=99)),
        ],
        value=Reference(name="arr"),
    )

    context: Context = {"arr": "arr0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Begin(
        effects=[
            Store(base=Reference(name="arr0"), index=0, value=Immediate(value=99)),
        ],
        value=Reference(name="arr0"),
    )

    assert actual == expected


def test_uniqify_program():
    program = Program(
        parameters=["x", "y"],
        body=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
    )

    _fresh, actual = uniqify_program(program)

    expected = Program(
        parameters=["x0", "y0"],
        body=Primitive(operator="+", left=Reference(name="x0"), right=Reference(name="y0")),
    )

    assert actual == expected
