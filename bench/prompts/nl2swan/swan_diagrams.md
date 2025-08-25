---
applyTo: "**/*.swan,**/*.swani,**/*.swant"
---

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