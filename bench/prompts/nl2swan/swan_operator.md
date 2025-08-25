---
applyTo: "**/*.swan,**/*.swani,**/*.swant"
---

# Swan operator declaration and definition

References:

- general definitions: [Swan definitions](./swan_definitions.md)
- type declarations: [Swan types](./swan_types.md)


## Swan operator kind
A Swan operator is of kind `node` or of kind `function`.

## Swan operator interface

The declaration of a a Swan operator is:

    *kind* name (inputs) `return` (outputs)

Inputs and outputs are list of semi-colon separated signals. A signal as a name, followed by a colon and its type.

Optionally, a signal can be followed by `default =` and expression or by `last = ` and an expresion.

Type of input or output is either a predefined type or a type that has been declared using a `type` declaration.

## Swan operator declaration

A Swan operator declaration is a Swan operator interface followed by `;`

## Swan operator definition

A Swan operator definition is a Swan operator interface
followed by a body, which defined as a **scope**. A scope
encloses different *sections* between `{}`

## Swan scope

A scope enclose different *sections* between `{}`. Sections can be

- `let` section to define Swan equations
- `var` section to define Swan variables


## Swan equations

In the Swan language, equations are a combination of operations and
calls to existing operators.

Equations are combined into `let` sections. A `let` section starts with the `let` keyword on single line, followed by the list of equations,
one equation per line, ended with `;`

## Swan variables

Swan variables are introduced by a `var` section, within a 
scope. 

In a `var` section, one has one variable declaration per line. 

A variable declaration is the variable name, followed by a colon and its type.

Optionally, a variable definition can be followed by `default =` plus an expression or by `last = ` plus an expresion.

Type of variable is either a predefined type or a type that has been declared using a `type` declaration.

Finally, a variable declaration ends with `;`.

