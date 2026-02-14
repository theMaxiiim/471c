*Brief Description*
The L2 language currently lacks a processing entry point, however, we assume it is ingested similarly to L3.
The general processing framework for all of the languages (L0 to L3) is driven by parsing a plain-text file, interpreting its parts, and, subsequently, assembling an abstract syntax tree (using py's ast) so to produce valid Python code.

Program is our primary organizing structure, with parameters and a body composed of Terms. Terms are expression-based and appear to be arbitrarily nestable. Terms include:
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    Load,
    Primitive,
    Reference,
    Store

*L2 vs L3*
L2 is the result of desugaring L3's `LetRec`. Where L3 supports mutually recursive bindings via LetRec, L2 eliminates this by lowering recursive bindings into explicit memory operations, where we allocate heap space for the bound values, storing them after definition, and loading them on reference. All other Terms are shared between the two languages unchanged.