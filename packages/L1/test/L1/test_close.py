from __future__ import annotations

import pytest
from L0 import syntax as L0
from L1 import close as close_module
from L1.close import close_program, free_variables
from L1.syntax import Abstract, Allocate, Apply, Branch, Copy, Halt, Immediate, Load, Primitive, Program, Store


def test_free_variables_halt():
    assert free_variables(Halt(value="x")) == ("x",)


def test_free_variables_invalid_statement_raises_type_error():
    with pytest.raises(TypeError, match="free_variables"):
        free_variables(object())  # type: ignore[arg-type]


def test_free_variables_excludes_abstract_bindings():
    statement = Immediate(
        destination="y",
        value=1,
        then=Abstract(
            destination="f",
            parameters=("x",),
            body=Primitive(
                destination="z",
                operator="+",
                left="x",
                right="y",
                then=Halt(value="z"),
            ),
            then=Halt(value="f"),
        ),
    )

    assert free_variables(statement) == ()


def test_free_variables_apply_deduplicates_names():
    statement = Apply(target="f", arguments=("f", "x", "f", "x"))
    assert free_variables(statement) == ("f", "x")


def test_free_variables_covers_remaining_statement_forms():
    statement = Copy(
        destination="tmp",
        source="src",
        then=Branch(
            operator="<",
            left="lhs",
            right="rhs",
            then=Allocate(
                destination="arr",
                count=2,
                then=Load(
                    destination="elt",
                    base="arr",
                    index=0,
                    then=Store(
                        base="arr",
                        index=1,
                        value="src",
                        then=Halt(value="elt"),
                    ),
                ),
            ),
            otherwise=Immediate(
                destination="k",
                value=0,
                then=Primitive(
                    destination="sum",
                    operator="+",
                    left="k",
                    right="rhs",
                    then=Halt(value="sum"),
                ),
            ),
        ),
    )

    assert free_variables(statement) == ("src", "lhs", "rhs")


def test_close_alias_is_close_program():
    assert close_module.close is close_program


def test_close_program_halt_only():
    result = close_program(Program(parameters=("x",), body=Halt(value="x")))

    assert len(result.procedures) == 1
    proc = result.procedures[0]
    assert proc.name == "l0"
    assert tuple(proc.parameters) == ("x",)
    assert isinstance(proc.body, L0.Halt)
    assert proc.body.value == "x"


def test_close_program_passthrough_forms():
    body = Copy(
        destination="a",
        source="x",
        then=Immediate(
            destination="one",
            value=1,
            then=Primitive(
                destination="s",
                operator="+",
                left="a",
                right="one",
                then=Branch(
                    operator="==",
                    left="s",
                    right="x",
                    then=Allocate(
                        destination="arr",
                        count=3,
                        then=Store(
                            base="arr",
                            index=0,
                            value="s",
                            then=Load(
                                destination="v",
                                base="arr",
                                index=0,
                                then=Halt(value="v"),
                            ),
                        ),
                    ),
                    otherwise=Halt(value="s"),
                ),
            ),
        ),
    )
    result = close_program(Program(parameters=("x",), body=body))

    assert len(result.procedures) == 1
    proc = result.procedures[0]
    assert proc.name == "l0"

    node = proc.body
    assert isinstance(node, L0.Copy)
    node = node.then
    assert isinstance(node, L0.Immediate)
    node = node.then
    assert isinstance(node, L0.Primitive)
    node = node.then
    assert isinstance(node, L0.Branch)
    assert isinstance(node.then, L0.Allocate)
    assert isinstance(node.otherwise, L0.Halt)


def test_close_program_abstract_no_captures():
    body = Abstract(
        destination="f",
        parameters=("y",),
        body=Halt(value="y"),
        then=Halt(value="f"),
    )
    result = close_program(Program(parameters=("x",), body=body))

    assert len(result.procedures) == 2
    assert result.procedures[-1].name == "l0"

    lifted = result.procedures[0]
    assert len(lifted.parameters) == 2
    assert lifted.parameters[1] == "y"

    l0_body = result.procedures[-1].body
    assert isinstance(l0_body, L0.Allocate)
    assert l0_body.destination == "f"
    assert l0_body.count == 1


def test_close_program_abstract_with_captures_and_apply():
    body = Abstract(
        destination="f",
        parameters=("y",),
        body=Primitive(
            destination="r",
            operator="+",
            left="x",
            right="y",
            then=Halt(value="r"),
        ),
        then=Apply(target="f", arguments=("x",)),
    )
    result = close_program(Program(parameters=("x",), body=body))

    assert len(result.procedures) == 2
    assert result.procedures[-1].name == "l0"

    lifted = result.procedures[0]
    assert len(lifted.parameters) == 2

    node = lifted.body
    assert isinstance(node, L0.Copy)
    node = node.then
    assert isinstance(node, L0.Load)
    node = node.then
    assert isinstance(node, L0.Primitive)

    l0_body = result.procedures[-1].body
    assert isinstance(l0_body, L0.Allocate)
    assert l0_body.count == 2

    node = l0_body
    while not isinstance(node, L0.Call):
        node = getattr(node, "then", None)
        assert node is not None, "expected a Call node at the end"
    assert len(node.arguments) == 2


def test_close_program_nested_abstracts():
    inner = Abstract(
        destination="g",
        parameters=("z",),
        body=Halt(value="z"),
        then=Halt(value="g"),
    )
    outer = Abstract(
        destination="f",
        parameters=("y",),
        body=inner,
        then=Halt(value="f"),
    )
    result = close_program(Program(parameters=("x",), body=outer))

    assert len(result.procedures) == 3
    assert result.procedures[-1].name == "l0"


def test_close_program_invalid_raises_type_error():
    with pytest.raises(TypeError, match="close_program"):
        close_program(object())  # type: ignore[arg-type]
