---
applyTo: "**/*.swan,**/*.swani,**/*.swant"
---

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
