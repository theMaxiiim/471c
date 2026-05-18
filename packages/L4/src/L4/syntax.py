from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, Field

type Identifier = Annotated[str, Field(min_length=1)]

type Nat = Annotated[int, Field(ge=0)]


class Program(BaseModel, frozen=True):
    tag: Literal["l4"] = "l4"
    parameters: Sequence[Identifier]
    body: Term


type Term = Annotated[
    Let
    | Reference
    | Abstract
    | Apply
    | Immediate
    | Primitive
    | Branch
    | Allocate
    | Load
    | Store
    | Begin
    | LetRec
    | Label
    | Jump
    | Chan
    | Send
    | Recv
    | Close
    | Closed  # lifecycle
    | Spawn,  # concurrency
    Field(discriminator="tag"),
]


class Let(BaseModel, frozen=True):
    tag: Literal["let"] = "let"
    bindings: Sequence[tuple[Identifier, Term]]
    body: Term


class LetRec(BaseModel, frozen=True):
    tag: Literal["letrec"] = "letrec"
    bindings: Sequence[tuple[Identifier, Term]]
    body: Term


class Reference(BaseModel, frozen=True):
    tag: Literal["reference"] = "reference"
    name: Identifier


class Abstract(BaseModel, frozen=True):
    tag: Literal["abstract"] = "abstract"
    parameters: Sequence[Identifier]
    body: Term


class Apply(BaseModel, frozen=True):
    tag: Literal["apply"] = "apply"
    target: Term
    arguments: Sequence[Term]


class Immediate(BaseModel, frozen=True):
    tag: Literal["immediate"] = "immediate"
    value: int


class Primitive(BaseModel, frozen=True):
    tag: Literal["primitive"] = "primitive"
    operator: Literal["+", "-", "*"]
    left: Term
    right: Term


class Branch(BaseModel, frozen=True):
    tag: Literal["branch"] = "branch"
    operator: Literal["<", "=="]
    left: Term
    right: Term
    consequent: Term
    otherwise: Term


class Allocate(BaseModel, frozen=True):
    tag: Literal["allocate"] = "allocate"
    count: Nat


class Load(BaseModel, frozen=True):
    tag: Literal["load"] = "load"
    base: Term
    index: Nat


class Store(BaseModel, frozen=True):
    tag: Literal["store"] = "store"
    base: Term
    index: Nat
    value: Term


class Begin(BaseModel, frozen=True):
    tag: Literal["begin"] = "begin"
    effects: Sequence[Term]
    value: Term


# -- nonlocal exits --


class Label(BaseModel, frozen=True):
    tag: Literal["label"] = "label"
    name: Identifier
    body: Term


class Jump(BaseModel, frozen=True):
    tag: Literal["jump"] = "jump"
    target: Term
    value: Term


# concurrency ..


class Chan(BaseModel, frozen=True):
    tag: Literal["chan"] = "chan"
    capacity: Nat = 0


class Send(BaseModel, frozen=True):
    tag: Literal["send"] = "send"
    channel: Term
    value: Term


class Recv(BaseModel, frozen=True):
    tag: Literal["recv"] = "recv"
    channel: Term


class Spawn(BaseModel, frozen=True):
    tag: Literal["spawn"] = "spawn"
    body: Term


# minor feature #2


class Close(BaseModel, frozen=True):
    tag: Literal["close"] = "close"
    channel: Term


class Closed(BaseModel, frozen=True):
    tag: Literal["closed"] = "closed"
    channel: Term
