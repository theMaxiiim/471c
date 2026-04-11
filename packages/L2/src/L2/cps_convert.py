from collections.abc import Callable, Sequence
from functools import partial

from L1 import syntax as L1

from L2 import syntax as L2


def cps_convert_term(
    term: L2.Term,
    k: Callable[[L1.Identifier], L1.Statement],
    fresh: Callable[[str], str],
) -> L1.Statement:
    _term = partial(cps_convert_term, fresh=fresh)
    _terms = partial(cps_convert_terms, fresh=fresh)

    match term:
        case L2.Let(bindings=bindings, body=body):
            bindings_list = list(bindings)

            def go_let(bs: list[tuple[L2.Identifier, L2.Term]]) -> L1.Statement:
                if not bs:
                    return cps_convert_term(body, k, fresh)
                (name, value), *rest = bs
                return cps_convert_term(
                    value,
                    lambda v, n=name, r=rest: L1.Copy(
                        destination=n,
                        source=v,
                        then=go_let(r),
                    ),
                    fresh,
                )

            return go_let(bindings_list)

        case L2.Reference(name=name):
            return k(name)

        case L2.Abstract(parameters=parameters, body=body):
            t = fresh("t")
            k_param = fresh("k")
            return L1.Abstract(
                destination=t,
                parameters=[*parameters, k_param],
                body=cps_convert_term(
                    body,
                    lambda v, k_param=k_param: L1.Apply(target=k_param, arguments=[v]),
                    fresh,
                ),
                then=k(t),
            )

        case L2.Apply(target=target, arguments=arguments):
            k_name = fresh("k")
            t = fresh("t")
            return _term(
                target,
                lambda f, k_name=k_name, t=t: _terms(
                    list(arguments),
                    lambda args, f=f, k_name=k_name, t=t: L1.Abstract(
                        destination=k_name,
                        parameters=[t],
                        body=k(t),
                        then=L1.Apply(target=f, arguments=[*args, k_name]),
                    ),
                ),
            )

        case L2.Immediate(value=value):
            t = fresh("t")
            return L1.Immediate(destination=t, value=value, then=k(t))

        case L2.Primitive(operator=operator, left=left, right=right):
            return _term(
                left,
                lambda l: _term(
                    right,
                    lambda r, l=l: L1.Primitive(
                        destination=(t := fresh("t")),
                        operator=operator,
                        left=l,
                        right=r,
                        then=k(t),
                    ),
                ),
            )

        case L2.Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            j = fresh("j")
            t = fresh("t")
            return _term(
                left,
                lambda l, j=j, t=t: _term(
                    right,
                    lambda r, l=l, j=j, t=t: L1.Abstract(
                        destination=j,
                        parameters=[t],
                        body=k(t),
                        then=L1.Branch(
                            operator=operator,
                            left=l,
                            right=r,
                            then=cps_convert_term(
                                consequent,
                                lambda v, j=j: L1.Apply(target=j, arguments=[v]),
                                fresh,
                            ),
                            otherwise=cps_convert_term(
                                otherwise,
                                lambda v, j=j: L1.Apply(target=j, arguments=[v]),
                                fresh,
                            ),
                        ),
                    ),
                ),
            )

        case L2.Allocate(count=count):
            t = fresh("t")
            return L1.Allocate(destination=t, count=count, then=k(t))

        case L2.Load(base=base, index=index):
            return _term(
                base,
                lambda b: L1.Load(
                    destination=(t := fresh("t")),
                    base=b,
                    index=index,
                    then=k(t),
                ),
            )

        case L2.Store(base=base, index=index, value=value):
            return _term(
                base,
                lambda b: _term(
                    value,
                    lambda v, b=b: L1.Store(
                        base=b,
                        index=index,
                        value=v,
                        then=L1.Immediate(
                            destination=(t := fresh("t")),
                            value=0,
                            then=k(t),
                        ),
                    ),
                ),
            )

        case L2.Begin(effects=effects, value=value):  # pragma: no branch
            effects_list = list(effects)

            def go(effs: list[L2.Term]) -> L1.Statement:
                if not effs:
                    return cps_convert_term(value, k, fresh)
                first, *rest = effs
                return cps_convert_term(first, lambda _, r=rest: go(r), fresh)

            return go(effects_list)


def cps_convert_terms(
    terms: Sequence[L2.Term],
    k: Callable[[Sequence[L1.Identifier]], L1.Statement],
    fresh: Callable[[str], str],
) -> L1.Statement:
    _term = partial(cps_convert_term, fresh=fresh)
    _terms = partial(cps_convert_terms, fresh=fresh)

    match terms:
        case []:
            return k([])

        case [first, *rest]:
            return _term(first, lambda first: _terms(rest, lambda rest: k([first, *rest])))

        case _:  # pragma: no cover
            raise ValueError(terms)


def cps_convert_program(
    program: L2.Program,
    fresh: Callable[[str], str],
) -> L1.Program:
    _term = partial(cps_convert_term, fresh=fresh)

    match program:
        case L2.Program(parameters=parameters, body=body):  # pragma: no branch
            return L1.Program(
                parameters=parameters,
                body=_term(body, lambda value: L1.Halt(value=value)),
            )
