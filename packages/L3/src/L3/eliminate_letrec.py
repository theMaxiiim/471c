# noqa: F841
from collections.abc import Mapping
from functools import partial

from L2 import syntax as L2

from . import syntax as L3

type Context = Mapping[L3.Identifier, bool]


def eliminate_letrec_term(
    term: L3.Term,
    context: Context,
) -> L2.Term:
    recur = partial(eliminate_letrec_term, context=context)

    match term:
        case L3.Let(bindings=bindings, body=body):
            local = dict.fromkeys([name for name, _ in bindings], False)
            return L2.Let(
                bindings=[(name, recur(value)) for name, value in bindings],
                body=eliminate_letrec_term(body, {**context, **local}),
            )

        case L3.LetRec(bindings=bindings, body=body):
            local = dict.fromkeys([name for name, _ in bindings], True)
            inner_context = {**context, **local}
            recur_inner = partial(eliminate_letrec_term, context=inner_context)
            return L2.Let(
                bindings=[(name, L2.Allocate(count=1)) for name, _ in bindings],
                body=L2.Begin(
                    effects=[
                        L2.Store(
                            base=L2.Reference(name=name),
                            index=0,
                            value=recur_inner(value),
                        )
                        for name, value in bindings
                    ],
                    value=eliminate_letrec_term(body, inner_context),
                ),
            )

        case L3.Reference(name=name):
            if context.get(name):
                return L2.Load(base=L2.Reference(name=name), index=0)
            return L2.Reference(name=name)

        case L3.Abstract(parameters=parameters, body=body):
            local = dict.fromkeys(parameters, False)
            return L2.Abstract(
                parameters=parameters,
                body=eliminate_letrec_term(body, {**context, **local}),
            )

        case L3.Apply(target=target, arguments=arguments):
            return L2.Apply(target=recur(target), arguments=[recur(a) for a in arguments])

        case L3.Immediate(value=value):
            return L2.Immediate(value=value)

        case L3.Primitive(operator=_operator, left=left, right=right):
            return L2.Primitive(operator=_operator, left=recur(left), right=recur(right))

        case L3.Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            return L2.Branch(
                operator=operator,
                left=recur(left),
                right=recur(right),
                consequent=recur(consequent),
                otherwise=recur(otherwise),
            )

        case L3.Allocate(count=count):
            return L2.Allocate(count=count)

        case L3.Load(base=base, index=index):
            return L2.Load(
                base=recur(base),
                index=index,
            )

        case L3.Store(base=base, index=index, value=value):
            return L2.Store(base=recur(base), index=index, value=recur(value))

        case L3.Begin(effects=effects, value=value):  # pragma: no branch
            return L2.Begin(effects=[recur(e) for e in effects], value=recur(value))


def eliminate_letrec_program(
    program: L3.Program,
) -> L2.Program:
    match program:
        case L3.Program(parameters=parameters, body=body):  # pragma: no branch
            return L2.Program(
                parameters=parameters,
                body=eliminate_letrec_term(body, {}),
            )
