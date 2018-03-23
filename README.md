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

Examples
--------

The following examples reflect how corresponding [official `wallaroo` examples](https://docs.wallaroolabs.com/book/python/writing-your-own-stateful-application.html)
could be written using `wallaby`.

**A Stateless Application - Reverse Words**

```python
import struct

import wallaroo

from wallaby import *

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
def application_setup(args):
    in_host, in_port = wallaroo.tcp_parse_input_addrs(args)[0]
    out_host, out_port = wallaroo.tcp_parse_output_addrs(args)[0]

    ab = wallaroo.ApplicationBuilder("Reverse Word")
    ab.new_pipeline("reverse",
                    wallaroo.TCPSourceConfig(in_host, in_port, decoder))
    ab.to(reverse)
    ab.to_sink(wallaroo.TCPSinkConfig(out_host, out_port, encoder))
    return ab.build()


```

_P.S. For corresponding `wallaroo` example, see:_

 - [A Stateless Application - Reverse Words](https://docs.wallaroolabs.com/book/python/writing-your-own-application.html)
 - [Example on github](https://github.com/WallarooLabs/wallaroo/tree/0.4.0/examples/python/reverse/)

*****

API Reference
-------------



Thanks
------

 - hask
 - python-effect
 - wallaroo
