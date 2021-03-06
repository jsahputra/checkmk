# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore



checkname = 'docker_container_diskstat'


info = [
    ['[time]'],
    ['1527265297'],
    ['[io_service_bytes]'],
    ['8:0', 'Read', '193536'],
    ['8:0', 'Write', '0'],
    ['8:0', 'Sync', '0'],
    ['8:0', 'Async', '193536'],
    ['8:0', 'Total', '193536'],
    ['253:11', 'Read', '193536'],
    ['253:11', 'Write', '0'],
    ['253:11', 'Sync', '0'],
    ['253:11', 'Async', '193536'],
    ['253:11', 'Total', '193536'],
    ['253:12', 'Read', '193536'],
    ['253:12', 'Write', '0'],
    ['253:12', 'Sync', '0'],
    ['253:12', 'Async', '193536'],
    ['253:12', 'Total', '193536'],
    ['253:14', 'Read', '31657984'],
    ['253:14', 'Write', '0'],
    ['253:14', 'Sync', '0'],
    ['253:14', 'Async', '31657984'],
    ['253:14', 'Total', '31657984'],
    ['Total', '32238592'],
    ['[io_serviced]'],
    ['8:0', 'Read', '19'],
    ['8:0', 'Write', '0'],
    ['8:0', 'Sync', '0'],
    ['8:0', 'Async', '19'],
    ['8:0', 'Total', '19'],
    ['253:11', 'Read', '19'],
    ['253:11', 'Write', '0'],
    ['253:11', 'Sync', '0'],
    ['253:11', 'Async', '19'],
    ['253:11', 'Total', '19'],
    ['253:12', 'Read', '19'],
    ['253:12', 'Write', '0'],
    ['253:12', 'Sync', '0'],
    ['253:12', 'Async', '19'],
    ['253:12', 'Total', '19'],
    ['253:14', 'Read', '998'],
    ['253:14', 'Write', '0'],
    ['253:14', 'Sync', '0'],
    ['253:14', 'Async', '998'],
    ['253:14', 'Total', '998'],
    ['Total', '1055'],
    ['[names]'],
    ['dm-0', '253:0'],
    ['dm-1', '253:1'],
    ['dm-10', '253:10'],
    ['dm-11', '253:11'],
    ['dm-12', '253:12'],
    ['dm-13', '253:13'],
    ['dm-14', '253:14'],
    ['dm-15', '253:15'],
    ['dm-16', '253:16'],
    ['dm-17', '253:17'],
    ['dm-18', '253:18'],
    ['dm-19', '253:19'],
    ['dm-2', '253:2'],
    ['dm-20', '253:20'],
    ['dm-21', '253:21'],
    ['dm-22', '253:22'],
    ['dm-23', '253:23'],
    ['dm-24', '253:24'],
    ['dm-3', '253:3'],
    ['dm-4', '253:4'],
    ['dm-5', '253:5'],
    ['dm-6', '253:6'],
    ['dm-7', '253:7'],
    ['dm-8', '253:8'],
    ['dm-9', '253:9'],
    ['sda', '8:0'],
]


discovery = {'': [('SUMMARY', 'diskstat_default_levels')]}


mock_item_state = {
    '': (1527265295, 0),
}


checks = {
    '': [
        ('SUMMARY', {}, [
            (0, 'Read: 15.37 MB/s', [
                ('disk_read_throughput', 16119296.0, None, None, None, None)]),
            (0, 'Write: 0.00 B/s', [
                ('disk_write_throughput', 0.0, None, None, None, None)]),
            (0, 'Read operations: 527.50 1/s', [
                ('disk_read_ios', 527.5, None, None, None, None)]),
            (0, 'Write operations: 0.00 1/s', [
                ('disk_write_ios', 0.0, None, None, None, None)]),
        ]),
    ],
}
