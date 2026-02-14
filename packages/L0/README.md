*Brief Description*
The L0 language currently lacks a processing entry point, however, we assume it is ingested similarly to L3.
The general processing framework for all of the languages (L0 to L3) is driven by parsing a plain-text file, interpreting its parts, and, subsequently, assembling an abstract syntax tree (using py's ast) so to produce valid Python code.

Program is our primary organizing structure, in which we store a flat list of Procedures. Each Procedure has a name, parameters, and a body composed of Statements. Statements include:
    Address,
    Allocate,
    Branch,
    Call,
    Copy,
    Halt,
    Immediate,
    Load,
    Primitive,
    Store

*L0 vs L1*
Where L1 supports nested, first-class functions via `Abstract` and tail calls via `Apply`, L0 eliminates these for a flat procedure list. `Abstract` is replaced by `Address`, which loads a reference to a top-level procedure, and `Apply` is replaced by `Call`, which seems to performs a call through that reference. Free variables captured by L1 closures are made explicit through the existing memory operations (Allocate, Load, Store). 

Besides that, other statement types are shared between the two languages remain unchanged.