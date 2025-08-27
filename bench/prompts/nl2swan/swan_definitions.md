---
applyTo: "**/*.swan,**/*.swani,**/*.swant"
---

# Swan language definitions

An `identifier` in the Swan language is a sequence of letters (a to z, A to Z), digits (0 to 9), and `_`. 

An `identifier` cannot start with `_`.

A `path_identifier` is a list of identifiers separated with `::`.

Swan comments:
- are one single line, starting with `--`
- or multiline like C, using the pair `/*`, `*/`

# Swan diagrams

A Swan diagram expresses equations in terms of block connections and
wires. This can be used as a graphical representation with a proper graphical editor.

## Diagram specification
A diagram is a specific scope section inside an operator, like the `let` or 
`var` section.

The diagram section starts with the `diagram` keyword and it is followed
by a list of objects, one per line, with the general form:

    (#lunum description locals)

*locals* are optional, and is defined by the keyword `where` followed by a list
of objects, as given previously

An `#lunum` is a unique identifier of an object, where *lunum* is an integer.

## Object of a diagram

The *description* of an object describes either blocks or connections.

## Block

Expression block: `(#lunum expr expression)` where expression is any valid Swan expression. For instance: `(#1 expr i0+42)`

Block call `(#lunum block operator_name)`, where operator_name is any Swan operator defined by the user, from a `node name1` or `function name2` declaration.
For instance a block declaration is: `(#2 block G)` or `(#2 block M::G)` if G is defined in some module M. 

Definition block is used to set variables or outputs, and as the form `(#lunum def variable_name)`. 
For instance, `def` block can be: `(#3  def o0)`.

Group block like `(#lunum group)` for group operations detailed later.

Wire are used to performe connection. A wire is defined by: `(#lunum wire source => target list)`
Wire source is an object reference, using the corresponding *lunum*.
Target list is a comma-separated list of an object reference, using the corresponding *lunum*.

## Diagram sections
A diagram can also contain a Swan section. In that case the description part is directly the section. 
For instance for variable section.
   (var x: int32;)



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




# Swan language types

This document presents the Swan language types and how to construct them.

## Predefined types

Swan language knows the predefined types:

- bool
- char
- int8, int16, int32, int64
- uint8, uint16, uint32, uint64
- float32, float64

## Type declaration

A type is declared with:
- the `type` keyword 
- its name, followed by  `=` and a type definition.

The declaration ends with `;`

A type without type definition is a type declaration. 

Predefined type are not defined using `type`

## Type definition

A type definition is

- a type expression
- a structure definition
- an enumeration definition
- a variant definition

A type expression is defined as:
- any predefined type
- a type name, in the form of an identifier or a *path_identifier*
- an array type definition

## Structure type definition

A structure expression is a comma separated list of fields
between `{` and `}`

A field has a name, followed by ':' and a type expression.

## Enumeration definition

A Swan enumeration starts with `enum` followed by a list of coma-separated names. List is between `{` and `}`.


## Array type definition

An array type expression is a type expression followed by `^` and
the size. The size is an integer, which can be an integer or a 
declared constant.

## Variant type definition

A variant type expression is used to denotes an union of types. 
A variant is a `|`-separated list of variant patterns, where
a varian pattern if of one of the form:

- empty variant: an identifier followed by `{}`
- variant with capture: an identifier followed by `{}` enclosing a type expression
- structure variant: and identifier followed a structure type definition

For a variant, it is required to start the identifier with a capital letter.
