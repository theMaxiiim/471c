*Brief Description*
L3 is the highest-level language in the pipeline and serves as the processing entry point.
The general processing framework for all of the languages (L0 to L3) is driven by parsing a plain-text file, interpreting its parts, and, subsequently, assembling an abstract syntax tree (using py's ast) so to produce valid Python code.

Program is our primary organizing structure, with parameters and a body composed of Terms. Terms are expression-based and arbitrarily nestable. Terms include:
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
    Store

L3 is nearly identical to L2, though, the only difference is the addition of `LetRec`, which supports mutually recursive bindings. The L3 to L2 pass eliminates LetRec by desugaring recursive bindings into explicit heap allocation, storage, and loading using Allocate, Store, and Load.