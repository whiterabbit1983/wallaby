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
pipeA = P[ T.int >> T.bool ]
pipeB = P[ T.bool >> T.str ]

# Composition
# >> :: pipe[A >= B] >= pipe[B >= C] >= pipe[A >= C]
pipeC = pipeA >> pipeB

# << :: pipe[B >= C] >= pipe[A >= B] >= pipe[A >= C]
pipeC = pipeB << pipeA

# invalid composition
pipeD = pipeB >> pipeA  # Will raise error

# Either compose
# | :: P[ A >= B ] >= P[ C >= D ] >= P[ Either[A, B] >= Either[C, D] ]
pipeE = P[ T.int >> T.bool ] | P[ T.str >> T.str ]
pipeE == P[ T.Either[int, str] >> T.Either[bool, str] ]

# Coerced composition
# >> :: pipe[A >> Maybe[B]] >> pipe[B >> C] >> pipe[A >> Maybe[C]]
# >> :: pipe[A >> Either[B, D]] >> ( pipe[B >> C] | pipe[D >> E] ) >> pipe[A >> Either[C, E]]

# State composition
class AllVotes(object):
    ...

stateful_sig = T[int] >> T.State[AllVotes] >> T[int, bool]

# State partitioning
# the partition function must be decorated with wallaroo.partition
@wallaroo.partition
def partition(data):
    return data.letter[0]

letter_partitions = list(string.ascii_lowercase)

partitioned_sig = T[int] >> T.State[TotalVotes, partition, letter_partitions] >> T[int, bool]
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

from wallaby import T, computation, Source, Sink

@wallaroo.decoder(header_length=4, length_fmt=">I")
def decoder(bs):
    return bs.decode("utf-8")

@wallaroo.encoder
def encoder(data):
    # data is a string
    return data + "\n"

@computation(T.str >= T.str)
def reverse(data):
    return data[::-1]

def application_setup(args):
    in_host, in_port = wallaroo.tcp_parse_input_addrs(args)[0]
    out_host, out_port = wallaroo.tcp_parse_output_addrs(args)[0]

    ab = wallaroo.ApplicationBuilder("Reverse Word")

    # Setup wallaroo application
    source_config = wallaroo.TCPSourceConfig(in_host, in_port, decoder)
    sink_config = wallaroo.TCPSinkConfig(out_host, out_port, encoder)

    reverse_pipeline = Source(source_config, 'reversed pipeline') >> reverse >> Sink(sink_config)
    reverse_pipeline.init( ab )

    return ab.build()

```

**A Stateful Application - Alphabet**

_Work in progress_

```python
import struct

import wallaroo
from wallaby import Source, Sink, T, computation


def application_setup(args):
    in_host, in_port = wallaroo.tcp_parse_input_addrs(args)[0]
    out_host, out_port = wallaroo.tcp_parse_output_addrs(args)[0]

    source_config = wallaroo.TCPSourceConfig(in_host, in_port, decoder)
    sink_config = wallaroo.TCPSinkConfig(out_host, out_port, encoder)
    ab = wallaroo.ApplicationBuilder("alphabet")
    alphabet_pipeline = Source(source_config, "alphabet") >> add_votes >> Sink(sink_config)
    alphabet_pipeline.init(ab)
    return ab.build()


class Votes(object):
    def __init__(self, letter, votes):
        self.letter = letter
        self.votes = votes


class AllVotes(object):
    def __init__(self):
        self.votes_by_letter = {}

    def update(self, votes):
        letter = votes.letter
        vote_count = votes.votes
        votes_for_letter = self.votes_by_letter.get(letter, Votes(letter, 0))
        votes_for_letter.votes += vote_count
        self.votes_by_letter[letter] = votes_for_letter

    def get_votes(self, letter):
        vbl = self.votes_by_letter[letter]
        # Return a new Votes instance here!
        return Votes(letter, vbl.votes)


@wallaroo.decoder(header_length=4, length_fmt=">I")
def decoder(bs):
    (letter, vote_count) = struct.unpack(">sI", bs)
    return Votes(letter, vote_count)


@computation(T[Votes] >> T.State[AllVotes] >> T[Votes, bool])
def add_votes(data, state):
    state.update(data)
    return (state.get_votes(data.letter), True)


@wallaroo.encoder
def encoder(data):
    # data is a Votes
    return struct.pack(">IsQ", 9, data.letter, data.votes)
```

**A Partitioned Stateful Application - Alphabet**

_Work in progress_

```python
import string
import struct

import wallaroo
from wallaby import Source, Sink, T, computation


def application_setup(args):
    in_host, in_port = wallaroo.tcp_parse_input_addrs(args)[0]
    out_host, out_port = wallaroo.tcp_parse_output_addrs(args)[0]

    source_config = wallaroo.TCPSourceConfig(in_host, in_port, decoder)
    sink_config = wallaroo.TCPSinkConfig(out_host, out_port, encoder)
    ab = wallaroo.ApplicationBuilder("alphabet")
    alphabet_pipeline = Source(source_config, "alphabet") >> add_votes >> Sink(sink_config)
    alphabet_pipeline.init(ab)
    return ab.build()


@wallaroo.partition
def partition(data):
    return data.letter[0]


class TotalVotes(object):
    def __init__(self):
        self.letter = "X"
        self.votes = 0

    def update(self, votes):
        self.letter = votes.letter
        self.votes += votes.votes

    def get_votes(self):
        return Votes(self.letter, self.votes)


class Votes(object):
    def __init__(self, letter, votes):
        self.letter = letter
        self.votes = votes


@wallaroo.decoder(header_length=4, length_fmt=">I")
def decoder(bs):
    (letter, vote_count) = struct.unpack(">sI", bs)
    return Votes(letter, vote_count)


letter_partitions = list(string.ascii_lowercase)
@computation(T[Votes] >> T.State[AllVotes, partition, letter_partitions] >> T[Votes, bool])
def add_votes(data, state):
    state.update(data)
    return (state.get_votes(), True)


@wallaroo.encoder
def encoder(data):
    # data is a Votes
    return struct.pack(">IsQ", 9, data.letter, data.votes)

```

_P.S. For corresponding `wallaroo` example, see:_

 - [A Stateless Application - Reverse Words](https://docs.wallaroolabs.com/book/python/writing-your-own-application.html)
 - [A Stateful Application - Alphabet](https://docs.wallaroolabs.com/book/python/writing-your-own-stateful-application.html)
 - [A Partitioned Stateful Application - Alphabet](https://docs.wallaroolabs.com/book/python/writing-your-own-partitioned-stateful-application.html)
 - [Examples on github](https://github.com/WallarooLabs/wallaroo/tree/0.4.0/examples/python)

*****

FAQs
----


API Reference
-------------



Thanks
------

 - [hask](https://github.com/billpmurphy/hask/blob/master/README.md)
 - [wallaroo](https://docs.wallaroolabs.com/book/python/api.html#wallarooapplicationbuilder)
