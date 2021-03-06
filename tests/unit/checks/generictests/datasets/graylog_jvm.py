# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore


checkname = 'graylog_jvm'

info = [
    [
        u'{"jvm.memory.heap.init": 1073741824, "jvm.memory.heap.used": 461934992, "jvm.memory.heap.max": 1020067840, "jvm.memory.heap.committed": 1020067840, "jvm.memory.heap.usage": 0.45284732435050595}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (
                    0, 'Used heap space: 440.54 MB', [
                        ('mem_heap', 461934992, None, None, None, None)
                    ]
                ),
                (
                    0, 'Committed heap space: 972.81 MB', [
                        (
                            'mem_heap_committed', 1020067840, None, None, None,
                            None
                        )
                    ]
                )
            ]
        )
    ]
}
