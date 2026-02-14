*Brief Description*
The L1 language currently lacks a processing entry point, however, we assume it is ingested similarly to L3.
The general processing framework for all of the languages (L0 to L3) is driven by parsing a plain-text file, interpreting its parts, and, subsequently, assembling an abstract syntax tree (using py's ast) so to produce valid Python code.

Program is our primary organizing structure, with parameters and a body composed of Statements. Most statements carry a `then` field pointing to the next Statement, forming a continuance of some sort. Statements include:
    Abstract,
    Allocate,
    Apply,
    Branch,
    Copy,
    Halt,
    Immediate,
    Load,
    Primitive,
    Store

*L1 vs L2*
L1 is the result of flattening L2's nested expression tree into a seemingly sequential style. Where L2's Terms are arbitrarily nested expressions (for instance, Apply takes a Term as its target, Primitive takes Terms as operands), L1's Statements operate only on flat Identifiers;; all intermediate values are given explicit names and destinations. L2's `Let` and `Reference` are eliminated; bindings become `Copy` assignments in the continuation chain. L2's `Begin` disappears, absorbed into the linear statement ordering. Halt is introduced to explicitly terminate execution. The remaining operations (Abstract, Apply, Immediate, Primitive, Branch, Allocate, Load, Store) are shared but restructured. Specifically, L2 versions are expression-based, L1 versions are statement-based with named destinations and `then` continuations.