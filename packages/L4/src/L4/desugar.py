from L3 import syntax as L3

from . import syntax as L4

# ast helpers!


def _ref(name: str) -> L3.Reference:
    return L3.Reference(name=name)


def _int(v: int) -> L3.Immediate:
    return L3.Immediate(value=v)


def _load(base: L3.Term, idx: int) -> L3.Load:
    return L3.Load(base=base, index=idx)


def _store(base: L3.Term, idx: int, val: L3.Term) -> L3.Store:
    return L3.Store(base=base, index=idx, value=val)


RQ = _ref("__rq")


# run queue (LL stack)


def _push(k: L3.Term) -> L3.Term:
    node = _ref("__node")
    return L3.Let(
        bindings=[("__node", L3.Allocate(count=2))],
        body=L3.Begin(
            effects=[
                _store(node, 0, k),
                _store(node, 1, _load(RQ, 0)),
            ],
            value=_store(RQ, 0, node),
        ),
    )


def _trampoline() -> L3.Term:
    top = _ref("__top")
    return L3.Branch(
        operator="==",
        left=_load(RQ, 0),
        right=_int(0),
        consequent=_int(0),
        otherwise=L3.Let(
            bindings=[("__top", _load(RQ, 0))],
            body=L3.Let(
                bindings=[
                    ("__k", _load(top, 0)),
                    ("__next", _load(top, 1)),
                ],
                body=L3.Begin(
                    effects=[_store(RQ, 0, _ref("__next"))],
                    value=L3.Jump(target=_ref("__k"), value=_int(0)),
                ),
            ),
        ),
    )


# unbuffered protocols


def _send_rendezvous(ch: L3.Term, v: L3.Term) -> L3.Term:
    return L3.Let(
        bindings=[("__k_recv", _load(ch, 1))],
        body=L3.Begin(
            effects=[
                _store(ch, 0, v),
                _store(ch, 2, _int(0)),
            ],
            value=L3.Label(
                name="__k_send",
                body=L3.Begin(
                    effects=[_push(_ref("__k_send"))],
                    value=L3.Jump(target=_ref("__k_recv"), value=v),
                ),
            ),
        ),
    )


def _send_park(ch: L3.Term, v: L3.Term) -> L3.Term:
    return L3.Begin(
        effects=[_store(ch, 0, v)],
        value=L3.Label(
            name="__k_send",
            body=L3.Begin(
                effects=[
                    _store(ch, 1, _ref("__k_send")),
                    _store(ch, 2, _int(1)),
                ],
                value=_trampoline(),
            ),
        ),
    )


def _send_unbuffered(ch: L3.Term, v: L3.Term) -> L3.Term:
    return L3.Branch(
        operator="==",
        left=_load(ch, 2),
        right=_int(2),
        consequent=_send_rendezvous(ch, v),
        otherwise=_send_park(ch, v),
    )


def _recv_rendezvous(ch: L3.Term) -> L3.Term:
    return L3.Let(
        bindings=[
            ("__rv", _load(ch, 0)),
            ("__k_send", _load(ch, 1)),
        ],
        body=L3.Begin(
            effects=[
                _store(ch, 2, _int(0)),
                _push(_ref("__k_send")),
            ],
            value=_ref("__rv"),
        ),
    )


def _recv_park(ch: L3.Term) -> L3.Term:
    return L3.Label(
        name="__k_recv",
        body=L3.Begin(
            effects=[
                _store(ch, 1, _ref("__k_recv")),
                _store(ch, 2, _int(2)),
            ],
            value=_trampoline(),
        ),
    )


def _recv_unbuffered(ch: L3.Term) -> L3.Term:
    return L3.Branch(
        operator="==",
        left=_load(ch, 2),
        right=_int(1),
        consequent=_recv_rendezvous(ch),
        otherwise=L3.Branch(
            operator="==",
            left=_load(ch, 3),
            right=_int(1),
            consequent=_int(0),
            otherwise=_recv_park(ch),
        ),
    )


# buffered protocols (capacity 1)


def _send_buffered(ch: L3.Term, v: L3.Term) -> L3.Term:
    # receiver waiting -> rendezvous as usual
    # buffer empty (state 0) -> non-blocking store
    # buffer full (state 1) -> park sender, stash pending in slot 5
    return L3.Branch(
        operator="==",
        left=_load(ch, 2),
        right=_int(2),
        consequent=_send_rendezvous(ch, v),
        otherwise=L3.Branch(
            operator="==",
            left=_load(ch, 2),
            right=_int(0),
            consequent=L3.Begin(
                effects=[
                    _store(ch, 0, v),
                    _store(ch, 2, _int(1)),
                ],
                value=_int(0),  # non-blocking
            ),
            otherwise=L3.Begin(
                effects=[_store(ch, 5, v)],  # stash pending value
                value=L3.Label(
                    name="__k_send_buf",
                    body=L3.Begin(
                        effects=[
                            _store(ch, 1, _ref("__k_send_buf")),
                            _store(ch, 2, _int(3)),  # state 3 = value + sender parked
                        ],
                        value=_trampoline(),
                    ),
                ),
            ),
        ),
    )


def _recv_value_ready(ch: L3.Term) -> L3.Term:
    # state 1 in buffered: value present, no sender parked
    return L3.Let(
        bindings=[("__rv", _load(ch, 0))],
        body=L3.Begin(
            effects=[_store(ch, 2, _int(0))],
            value=_ref("__rv"),
        ),
    )


def _recv_value_and_sender(ch: L3.Term) -> L3.Term:
    # state 3: value present + sender parked with pending in slot 5
    return L3.Let(
        bindings=[
            ("__rv", _load(ch, 0)),
            ("__k_send", _load(ch, 1)),
            ("__pending", _load(ch, 5)),
        ],
        body=L3.Begin(
            effects=[
                _store(ch, 0, _ref("__pending")),  # move pending into buffer
                _store(ch, 2, _int(1)),  # back to value ready
                _push(_ref("__k_send")),  # wake sender
            ],
            value=_ref("__rv"),
        ),
    )


def _recv_buffered(ch: L3.Term) -> L3.Term:
    # state 1 -> take value (no sender to wake)
    # state 3 -> take value + move pending + wake sender
    # closed -> 0
    # else -> park
    return L3.Branch(
        operator="==",
        left=_load(ch, 2),
        right=_int(1),
        consequent=_recv_value_ready(ch),
        otherwise=L3.Branch(
            operator="==",
            left=_load(ch, 2),
            right=_int(3),
            consequent=_recv_value_and_sender(ch),
            otherwise=L3.Branch(
                operator="==",
                left=_load(ch, 3),
                right=_int(1),
                consequent=_int(0),
                otherwise=_recv_park(ch),
            ),
        ),
    )


# main desugaring -


def desugar_term(term: L4.Term) -> L3.Term:
    match term:
        case L4.Let(bindings=bindings, body=body):
            return L3.Let(
                bindings=[(n, desugar_term(v)) for n, v in bindings],
                body=desugar_term(body),
            )

        case L4.LetRec(bindings=bindings, body=body):
            return L3.LetRec(
                bindings=[(n, desugar_term(v)) for n, v in bindings],
                body=desugar_term(body),
            )

        case L4.Reference(name=name):
            return L3.Reference(name=name)

        case L4.Abstract(parameters=parameters, body=body):
            return L3.Abstract(parameters=parameters, body=desugar_term(body))

        case L4.Apply(target=target, arguments=arguments):
            return L3.Apply(
                target=desugar_term(target),
                arguments=[desugar_term(a) for a in arguments],
            )

        case L4.Immediate(value=value):
            return L3.Immediate(value=value)

        case L4.Primitive(operator=op, left=left, right=right):
            return L3.Primitive(operator=op, left=desugar_term(left), right=desugar_term(right))

        case L4.Branch(operator=op, left=left, right=right, consequent=c, otherwise=o):
            return L3.Branch(
                operator=op,
                left=desugar_term(left),
                right=desugar_term(right),
                consequent=desugar_term(c),
                otherwise=desugar_term(o),
            )

        case L4.Allocate(count=count):
            return L3.Allocate(count=count)

        case L4.Load(base=base, index=index):
            return L3.Load(base=desugar_term(base), index=index)

        case L4.Store(base=base, index=index, value=value):
            return L3.Store(base=desugar_term(base), index=index, value=desugar_term(value))

        case L4.Begin(effects=effects, value=value):
            return L3.Begin(effects=[desugar_term(e) for e in effects], value=desugar_term(value))

        case L4.Label(name=name, body=body):
            return L3.Label(name=name, body=desugar_term(body))

        case L4.Jump(target=target, value=value):
            return L3.Jump(target=desugar_term(target), value=desugar_term(value))

        # concurrency! core impl segment

        case L4.Chan(capacity=capacity):
            # 6 slots: value, cont, state, closed, capacity, pending
            ch = _ref("__ch")
            return L3.Let(
                bindings=[("__ch", L3.Allocate(count=6))],
                body=L3.Begin(
                    effects=[
                        _store(ch, 0, _int(0)),
                        _store(ch, 1, _int(0)),
                        _store(ch, 2, _int(0)),
                        _store(ch, 3, _int(0)),
                        _store(ch, 4, _int(capacity)),
                        _store(ch, 5, _int(0)),
                    ],
                    value=ch,
                ),
            )

        case L4.Send(channel=channel, value=value):
            ch = _ref("__sch")
            v = _ref("__sv")
            return L3.Let(
                bindings=[
                    ("__sch", desugar_term(channel)),
                    ("__sv", desugar_term(value)),
                ],
                body=L3.Branch(
                    operator="==",
                    left=_load(ch, 3),
                    right=_int(1),
                    consequent=_int(0),  # closed
                    otherwise=L3.Branch(
                        operator="==",
                        left=_load(ch, 4),
                        right=_int(0),
                        consequent=_send_unbuffered(ch, v),
                        otherwise=_send_buffered(ch, v),  # capacity > 0
                    ),
                ),
            )

        case L4.Recv(channel=channel):
            ch = _ref("__rch")
            return L3.Let(
                bindings=[("__rch", desugar_term(channel))],
                body=L3.Branch(
                    operator="==",
                    left=_load(ch, 4),
                    right=_int(0),
                    consequent=_recv_unbuffered(ch),
                    otherwise=_recv_buffered(ch),  # capacity > 0
                ),
            )

        case L4.Close(channel=channel):
            ch = _ref("__cch")
            return L3.Let(
                bindings=[("__cch", desugar_term(channel))],
                body=L3.Branch(
                    operator="==",
                    left=_load(ch, 2),
                    right=_int(2),
                    consequent=L3.Let(
                        bindings=[("__k_recv", _load(ch, 1))],
                        body=L3.Begin(
                            effects=[
                                _store(ch, 3, _int(1)),
                                _store(ch, 2, _int(0)),
                                _push(_ref("__k_recv")),
                            ],
                            value=_int(0),
                        ),
                    ),
                    otherwise=L3.Begin(
                        effects=[_store(ch, 3, _int(1))],
                        value=_int(0),
                    ),
                ),
            )

        case L4.Closed(channel=channel):
            ch = _ref("__clch")
            return L3.Let(
                bindings=[("__clch", desugar_term(channel))],
                body=_load(ch, 3),
            )

        case L4.Spawn(body=body):  # pragma: no branch
            return L3.Label(
                name="__k_parent",
                body=L3.Begin(
                    effects=[
                        _push(_ref("__k_parent")),
                        L3.Apply(target=desugar_term(body), arguments=[]),
                    ],
                    value=_trampoline(),
                ),
            )


def desugar_program(program: L4.Program) -> L3.Program:
    return L3.Program(
        parameters=program.parameters,
        body=L3.Let(
            bindings=[("__rq", L3.Allocate(count=1))],
            body=L3.Begin(
                effects=[_store(RQ, 0, _int(0))],
                value=desugar_term(program.body),
            ),
        ),
    )
