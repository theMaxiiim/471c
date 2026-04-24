from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Literal

from L0 import syntax as L0

from .syntax import Abstract, Allocate, Apply, Branch, Copy, Halt, Immediate, Load, Primitive, Program, Statement, Store

# operator types (matching L0 syntax)

PrimitiveOp = Literal["+", "-", "*"]
BranchOp = Literal["<", "=="]


# internal helpers


class _FreshNames:
    def __init__(self) -> None:
        self._counter: int = 0

    def __call__(self, hint: str) -> str:
        name = f"{hint}$close{self._counter}"
        self._counter += 1
        return name


class _LiftedProcedures:
    def __init__(self) -> None:
        self.items: list[L0.Procedure] = []

    def append(self, procedure: L0.Procedure) -> None:
        self.items.append(procedure)

    def extend(self, procedures: Iterable[L0.Procedure]) -> None:
        self.items.extend(procedures)


# ordered set-like operations on name tuples


def _merge(left: Iterable[str], right: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []

    for name in [*left, *right]:
        if name not in seen:
            seen.add(name)
            result.append(name)

    return tuple(result)


def _without(names: Iterable[str], excluded: Iterable[str]) -> tuple[str, ...]:
    excluded_set = set(excluded)
    return tuple(n for n in names if n not in excluded_set)


# l0 ast constructors


def _halt(value: str) -> L0.Halt:
    return L0.Halt(value=value)


def _copy(destination: str, source: str, then: L0.Statement) -> L0.Copy:
    return L0.Copy(destination=destination, source=source, then=then)


def _immediate(destination: str, value: int, then: L0.Statement) -> L0.Immediate:
    return L0.Immediate(destination=destination, value=value, then=then)


def _primitive(
    destination: str,
    operator: PrimitiveOp,
    left: str,
    right: str,
    then: L0.Statement,
) -> L0.Primitive:
    return L0.Primitive(
        destination=destination,
        operator=operator,
        left=left,
        right=right,
        then=then,
    )


def _branch(
    operator: BranchOp,
    left: str,
    right: str,
    then: L0.Statement,
    otherwise: L0.Statement,
) -> L0.Branch:
    return L0.Branch(
        operator=operator,
        left=left,
        right=right,
        then=then,
        otherwise=otherwise,
    )


def _allocate(destination: str, count: int, then: L0.Statement) -> L0.Allocate:
    return L0.Allocate(destination=destination, count=count, then=then)


def _load(destination: str, base: str, index: int, then: L0.Statement) -> L0.Load:
    return L0.Load(destination=destination, base=base, index=index, then=then)


def _store(base: str, index: int, value: str, then: L0.Statement) -> L0.Store:
    return L0.Store(base=base, index=index, value=value, then=then)


def _address(destination: str, name: str, then: L0.Statement) -> L0.Address:
    return L0.Address(destination=destination, name=name, then=then)


def _call(target: str, arguments: Sequence[str]) -> L0.Call:
    return L0.Call(target=target, arguments=arguments)


def _procedure(name: str, parameters: Sequence[str], body: L0.Statement) -> L0.Procedure:
    return L0.Procedure(name=name, parameters=parameters, body=body)


def _program(procedures: Sequence[L0.Procedure]) -> L0.Program:
    return L0.Program(procedures=procedures)


# free-variable analysis over l1 statements


def free_variables(statement: Statement) -> tuple[str, ...]:
    match statement:
        case Halt(value=value):
            return (value,)

        case Copy(destination=dst, source=src, then=rest):
            return _merge((src,), _without(free_variables(rest), (dst,)))

        case Immediate(destination=dst, value=_, then=rest):
            return _without(free_variables(rest), (dst,))

        case Primitive(destination=dst, operator=_, left=lhs, right=rhs, then=rest):
            return _merge((lhs, rhs), _without(free_variables(rest), (dst,)))

        case Branch(operator=_, left=lhs, right=rhs, then=consequent, otherwise=alternative):
            return _merge(
                (lhs, rhs),
                _merge(free_variables(consequent), free_variables(alternative)),
            )

        case Allocate(destination=dst, count=_, then=rest):
            return _without(free_variables(rest), (dst,))

        case Load(destination=dst, base=base, index=_, then=rest):
            return _merge((base,), _without(free_variables(rest), (dst,)))

        case Store(base=base, index=_, value=val, then=rest):
            return _merge((base, val), free_variables(rest))

        case Abstract(destination=dst, parameters=params, body=body, then=rest):
            body_fv = _without(free_variables(body), (dst, *params))
            rest_fv = _without(free_variables(rest), (dst,))
            return _merge(body_fv, rest_fv)

        case Apply(target=tgt, arguments=args):
            return _merge((tgt,), args)

        case _:  # pragma: no cover
            raise TypeError(f"free_variables: unexpected L1 node {type(statement).__name__}")


# closure helpers


def _prepend_capture_loads(
    body: L0.Statement,
    env_param: str,
    captures: Sequence[str],
) -> L0.Statement:
    result = body
    for i in range(len(captures) - 1, -1, -1):
        result = _load(
            destination=captures[i],
            base=env_param,
            index=i + 1,
            then=result,
        )
    return result


def _build_closure(
    destination: str,
    proc_name: str,
    captures: Sequence[str],
    continuation: L0.Statement,
    fresh: _FreshNames,
) -> L0.Statement:
    addr_tmp = fresh(f"{destination}$addr")

    result = continuation
    for i in range(len(captures) - 1, -1, -1):
        result = _store(base=destination, index=i + 1, value=captures[i], then=result)

    result = _store(base=destination, index=0, value=addr_tmp, then=result)
    result = _address(destination=addr_tmp, name=proc_name, then=result)
    result = _allocate(destination=destination, count=len(captures) + 1, then=result)

    return result


# closure conversion pass (l1 -> l0)


def _close_statement(
    statement: Statement,
    lifted: _LiftedProcedures,
    fresh: _FreshNames,
) -> L0.Statement:
    match statement:
        case Halt(value=value):
            return _halt(value=value)

        case Copy(destination=dst, source=src, then=rest):
            return _copy(
                destination=dst,
                source=src,
                then=_close_statement(rest, lifted, fresh),
            )

        case Immediate(destination=dst, value=val, then=rest):
            return _immediate(
                destination=dst,
                value=val,
                then=_close_statement(rest, lifted, fresh),
            )

        case Primitive(destination=dst, operator=op, left=lhs, right=rhs, then=rest):
            return _primitive(
                destination=dst,
                operator=op,
                left=lhs,
                right=rhs,
                then=_close_statement(rest, lifted, fresh),
            )

        case Branch(operator=op, left=lhs, right=rhs, then=consequent, otherwise=alternative):
            return _branch(
                operator=op,
                left=lhs,
                right=rhs,
                then=_close_statement(consequent, lifted, fresh),
                otherwise=_close_statement(alternative, lifted, fresh),
            )

        case Allocate(destination=dst, count=cnt, then=rest):
            return _allocate(
                destination=dst,
                count=cnt,
                then=_close_statement(rest, lifted, fresh),
            )

        case Load(destination=dst, base=base, index=idx, then=rest):
            return _load(
                destination=dst,
                base=base,
                index=idx,
                then=_close_statement(rest, lifted, fresh),
            )

        case Store(base=base, index=idx, value=val, then=rest):
            return _store(
                base=base,
                index=idx,
                value=val,
                then=_close_statement(rest, lifted, fresh),
            )

        case Abstract(destination=dst, parameters=params, body=body, then=rest):
            captures = _without(free_variables(body), (dst, *params))
            proc_name = fresh(dst)
            env_param = fresh(f"{dst}$env")

            nested = _LiftedProcedures()
            closed_body = _close_statement(body, nested, fresh)
            closed_body = _prepend_capture_loads(closed_body, env_param, captures)
            closed_body = _copy(destination=dst, source=env_param, then=closed_body)

            lifted.append(
                _procedure(
                    name=proc_name,
                    parameters=(env_param, *params),
                    body=closed_body,
                )
            )
            lifted.extend(nested.items)

            return _build_closure(
                destination=dst,
                proc_name=proc_name,
                captures=captures,
                continuation=_close_statement(rest, lifted, fresh),
                fresh=fresh,
            )

        case Apply(target=tgt, arguments=args):
            code_ptr = fresh(f"{tgt}$code")
            return _load(
                destination=code_ptr,
                base=tgt,
                index=0,
                then=_call(target=code_ptr, arguments=(tgt, *args)),
            )

        case _:
            raise TypeError(f"_close_statement: unexpected L1 node {type(statement).__name__}")


# entry point


def close_program(program: Program) -> L0.Program:
    match program:
        case Program(parameters=params, body=body):
            fresh = _FreshNames()
            lifted = _LiftedProcedures()

            closed_body = _close_statement(body, lifted, fresh)
            lifted.append(_procedure(name="l0", parameters=params, body=closed_body))

            return _program(procedures=tuple(lifted.items))

        case _:
            raise TypeError(f"close_program: expected Program, got {type(program).__name__}")


close = close_program
