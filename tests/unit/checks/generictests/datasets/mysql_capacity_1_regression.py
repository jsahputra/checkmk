# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore



checkname = 'mysql_capacity'


info = [['[[]]'],
        ['information_schema', '147456', '0'],
        ['mysql', '665902', '292'],
        ['performance_schema', '0', '0'],
        ['test', '409255936', '54525952']]


discovery = {
    '': [
        ('mysql:test', {}),
    ],
}


checks = {
    '': [
        (
            'mysql:test',
            {},
            [(0, 'Size: 390.30 MB', [('database_size', 409255936, None, None, None, None)])]
        ),
        (
            'mysql:test',
            (40960, 51200),
            [
                (
                    2,
                    'Size: 390.30 MB (warn/crit at 40.00 kB/50.00 kB)',
                    [('database_size', 409255936, 40960, 51200, None, None)]
                )
            ]
        ),
        (
            'mysql:test',
            (40960000000, 51200000000),
            [
                (
                    0,
                    'Size: 390.30 MB',
                    [('database_size', 409255936, 40960000000, 51200000000, None, None)]
                )
            ]
        ),
    ],
}
