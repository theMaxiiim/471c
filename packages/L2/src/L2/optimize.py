from .syntax import (
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
    Term,
)


def free_variables(term: Term) -> set[str]:
    match term:
        case Reference(name=name):
            return {name}

        case Immediate() | Allocate():
            return set()

        case Let(bindings=bindings, body=body):
            result = free_variables(body)
            for name, value in reversed(bindings):
                result.discard(name)
                result |= free_variables(value)
            return result

        case Abstract(parameters=parameters, body=body):
            return free_variables(body) - set(parameters)

        case Apply(target=target, arguments=arguments):
            result = free_variables(target)
            for arg in arguments:
                result |= free_variables(arg)
            return result

        case Primitive(left=left, right=right):
            return free_variables(left) | free_variables(right)

        case Branch(left=left, right=right, consequent=consequent, otherwise=otherwise):
            return free_variables(left) | free_variables(right) | free_variables(consequent) | free_variables(otherwise)

        case Load(base=base):
            return free_variables(base)

        case Store(base=base, value=value):
            return free_variables(base) | free_variables(value)

        case Begin(effects=effects, value=value):  # pragma: no branch
            result = free_variables(value)
            for e in effects:
                result |= free_variables(e)
            return result


def substitute(term: Term, name: str, replacement: Term) -> Term:
    match term:
        case Reference(name=n):
            return replacement if n == name else term

        case Immediate() | Allocate():
            return term

        case Let(bindings=bindings, body=body):
            new_bindings: list[tuple[str, Term]] = []
            shadowed = False
            for bname, bvalue in bindings:
                if not shadowed:
                    new_bindings.append((bname, substitute(bvalue, name, replacement)))
                else:
                    new_bindings.append((bname, bvalue))
                if bname == name:
                    shadowed = True
            new_body = body if shadowed else substitute(body, name, replacement)
            return Let(bindings=new_bindings, body=new_body)

        case Abstract(parameters=parameters, body=body):
            if name in parameters:
                return term
            return Abstract(
                parameters=parameters,
                body=substitute(body, name, replacement),
            )

        case Apply(target=target, arguments=arguments):
            return Apply(
                target=substitute(target, name, replacement),
                arguments=[substitute(a, name, replacement) for a in arguments],
            )

        case Primitive(operator=op, left=left, right=right):
            return Primitive(
                operator=op,
                left=substitute(left, name, replacement),
                right=substitute(right, name, replacement),
            )

        case Branch(operator=op, left=left, right=right, consequent=c, otherwise=o):
            return Branch(
                operator=op,
                left=substitute(left, name, replacement),
                right=substitute(right, name, replacement),
                consequent=substitute(c, name, replacement),
                otherwise=substitute(o, name, replacement),
            )

        case Load(base=base, index=index):
            return Load(
                base=substitute(base, name, replacement),
                index=index,
            )

        case Store(base=base, index=index, value=value):
            return Store(
                base=substitute(base, name, replacement),
                index=index,
                value=substitute(value, name, replacement),
            )

        case Begin(effects=effects, value=value):  # pragma: no branch
            return Begin(
                effects=[substitute(e, name, replacement) for e in effects],
                value=substitute(value, name, replacement),
            )


def optimize_term(term: Term) -> Term:
    match term:
        case Reference() | Immediate() | Allocate():
            return term

        case Let(bindings=bindings, body=body):
            # optimize all sub-terms bottom-up
            working: list[tuple[str, Term]] = [(n, optimize_term(v)) for n, v in bindings]
            opt_body = optimize_term(body)

            propagated: list[tuple[str, Term]] = []
            for i in range(len(working)):
                bname, bvalue = working[i]
                match bvalue:
                    case Immediate() | Reference():
                        rebound_at = len(working)
                        for j in range(i + 1, len(working)):
                            if working[j][0] == bname:
                                rebound_at = j
                                break
                        for j in range(i + 1, rebound_at):
                            sname, svalue = working[j]
                            working[j] = (sname, substitute(svalue, bname, bvalue))
                        if rebound_at == len(working):
                            opt_body = substitute(opt_body, bname, bvalue)
                    case _:
                        propagated.append((bname, bvalue))

            if not propagated:
                return opt_body

            live = free_variables(opt_body)
            kept: list[tuple[str, Term]] = []
            for bname, bvalue in reversed(propagated):
                if bname in live:
                    kept.append((bname, bvalue))
                    live |= free_variables(bvalue)
            kept.reverse()

            if not kept:
                return opt_body
            return Let(bindings=kept, body=opt_body)

        case Abstract(parameters=parameters, body=body):
            return Abstract(parameters=parameters, body=optimize_term(body))

        case Apply(target=target, arguments=arguments):
            return Apply(
                target=optimize_term(target),
                arguments=[optimize_term(a) for a in arguments],
            )

        case Primitive(operator=op, left=left, right=right):
            opt_left = optimize_term(left)
            opt_right = optimize_term(right)
            match (opt_left, opt_right):
                case (Immediate(value=a), Immediate(value=b)):
                    match op:
                        case "+":
                            return Immediate(value=a + b)
                        case "-":
                            return Immediate(value=a - b)
                        case "*":  # pragma: no branch
                            return Immediate(value=a * b)
                case _:
                    return Primitive(operator=op, left=opt_left, right=opt_right)

        case Branch(operator=op, left=left, right=right, consequent=c, otherwise=o):
            opt_left = optimize_term(left)
            opt_right = optimize_term(right)
            match (opt_left, opt_right):
                case (Immediate(value=a), Immediate(value=b)):
                    match op:
                        case "<":
                            return optimize_term(c) if a < b else optimize_term(o)
                        case "==":  # pragma: no branch
                            return optimize_term(c) if a == b else optimize_term(o)
                case _:
                    return Branch(
                        operator=op,
                        left=opt_left,
                        right=opt_right,
                        consequent=optimize_term(c),
                        otherwise=optimize_term(o),
                    )

        case Load(base=base, index=index):
            return Load(base=optimize_term(base), index=index)

        case Store(base=base, index=index, value=value):
            return Store(
                base=optimize_term(base),
                index=index,
                value=optimize_term(value),
            )

        case Begin(effects=effects, value=value):  # pragma: no branch
            return Begin(
                effects=[optimize_term(e) for e in effects],
                value=optimize_term(value),
            )


def optimize_program(
    program: Program,
) -> Program:
    match program:
        case Program(parameters=_parameters, body=_body):  # pragma: no branch
            current = program
            while True:
                optimized = Program(
                    parameters=current.parameters,
                    body=optimize_term(current.body),
                )
                if optimized == current:
                    return optimized
                current = optimized
