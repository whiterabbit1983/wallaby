wallaby
=======

A simple, functional wrapper around the [wallaroo](https://docs.wallaroolabs.com/book/python/api.html) API.
`wallaby` makes it easier to write concurrent code that is easy to reason about, straight-forward to document and make use of `wallaroo`'s more advanced features.
Under the hood, it uses type constraints and compile-time reflection to make these static guarantees.


`wallaroo` code written using `wallaby` constructs can:

 - Transparently compose pure (state-less) functions into single functions.
 - Automatically partition traversable outputs while preserving order-of-arrival.
 - Enforce side effect isolation.
 - Detect when a state change actually happened to optimize state persistence.
 - Provide robust, declarative error handling.

Notes on Type System
--------------------

```python

# Type Constructor
# T :: <Type constructor>

# Aliases
T.int = T[int]
T.str = T[str]

# Error encapsulation
maybe_int = T.Maybe[int]
either_int_or_error = T.Either[int, Exception]

# State encapsulation
stateful_int_and_history = T.State[int, T.list[int]]

# Pipe
pipeA = P[ T.int >= T.bool ]
pipeB = P[ T.bool >= T.str ]

# Composition
# >> :: pipe[A >= B] >= pipe[B >= C] >= pipe[A >= C]
pipeC = pipeA >> pipeB

# << :: pipe[B >= C] >= pipe[A >= B] >= pipe[A >= C]
pipeC = pipeB << pipeA

# invalid composition
pipeD = pipeB >> pipeA  # Will raise error

# Either compose
# | :: P[ A >= B ] >= P[ C >= D ] >= P[ Either[A, B] >= Either[C, D] ]
pipeE = P[ T.int >= T.bool ] | P[ T.str >= T.str ]
pipeE == P[ T.Either[int, str] >= T.Either[bool, str] ]

# Coerced composition
# >> :: pipe[A >= Maybe[B]] >= pipe[B >= C] >= pipe[A >= Maybe[C]]
# >> :: pipe[A >= Either[B, D]] >= ( pipe[B >= C] | pipe[D >= E] ) >= pipe[A >= Either[C, E]]

# State composition
# WIP

# State partitioning
# WIP
```

Examples
--------

The following examples reflect how corresponding [official `wallaroo` examples](https://docs.wallaroolabs.com/book/python/writing-your-own-stateful-application.html)
could be written using `wallaby`.

**A Stateless Application - Reverse Words**

_Work in progress_

```python
import struct

import wallaroo

from wallaby import T, pipeline, pipe, Source, Sink

@wallaroo.decoder(header_length=4, length_fmt=">I")
def decoder(bs):
    return bs.decode("utf-8")

@wallaroo.encoder
def encoder(data):
    # data is a string
    return data + "\n"

@pipe(T.str >= T.str)
def reverse(data):
    return data[::-1]

@pipeline
def make_reverse_pipeline( source, sink ):
    return source >> reverse >> sink

def application_setup(args):
    in_host, in_port = wallaroo.tcp_parse_input_addrs(args)[0]
    out_host, out_port = wallaroo.tcp_parse_output_addrs(args)[0]

    ab = wallaroo.ApplicationBuilder("Reverse Word")

    # Setup wallaroo application
    source_config = wallaroo.TCPSourceConfig(in_host, in_port, decoder)
    sink_config = wallaroo.TCPSinkConfig(out_host, out_port, encoder))

    reverse_pipeline = make_reverse_pipeline( Source( source_config ), Sink( sink_config ))
    reverse_pipeline.init( ab )

    return ab.build()

```

_P.S. For corresponding `wallaroo` example, see:_

 - [A Stateless Application - Reverse Words](https://docs.wallaroolabs.com/book/python/writing-your-own-application.html)
 - [Example on github](https://github.com/WallarooLabs/wallaroo/tree/0.4.0/examples/python/reverse/)

*****

FAQs
----


API Reference
-------------



Thanks
------

 - [hask](https://github.com/billpmurphy/hask/blob/master/README.md)
 - [python-effect](https://github.com/python-effect/effect)
 - [wallaroo](https://docs.wallaroolabs.com/book/python/api.html#wallarooapplicationbuilder)
