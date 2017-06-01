from argparse import ArgumentParser
from glob import iglob
from io import StringIO
from os import path

import arff
import pandas as pd
from influxdb import line_protocol

_DEFAULT_LABEL_KEY = 'Trainingdata'


def read_arff(filename):
    """
    Read a file containing an ARFF document and convert it to a dict. 
    :param str filename: the filename or path
    :return: dict
    """
    with open(filename, 'r') as inputFile, StringIO() as f:
        # TODO the liac-arff library does not support parsing dates right now.
        # Treat all dates as strings to allow parsing the file anyway.
        # This vastly reduces the parsing performance!
        f.write(inputFile.read().replace('DATE "yyyy-MM-dd HH:mm:ss.SSS"', 'STRING'))
        f.seek(0)
        return arff.load(f)


def arff_to_influxdb(arff_input, measurement, tags_keys=_DEFAULT_LABEL_KEY, time_key='Timestamp'):
    """
    Convert an ARFF dict to an InfluxDB line protocol string
    :param dict arff_input: the dict (returned from read_arff()) 
    :param str measurement: the name of the InfluxDB measurement 
    :param list[str] tags_keys: a list of keys to be used as InfluxDB tags
    :param str time_key: the key to be used as InfluxBD timestamp  
    :return: a multi-line string with InfluxBD line protocol entries
    """

    if not isinstance(tags_keys, list):
        tags_keys = [tags_keys]

    def convert_line(line):
        fields = {k: v for k, v in line.to_dict().items() if
                  not pd.isnull(v) and  # do not add fields with a None/NaN value, InfluxDB does not support this.
                  k not in tags_keys and  # do not add values we use as tags to the fields
                  k != time_key}  # do not add the time value to the fields

        return {
            'measurement': measurement,
            'tags': {k: line[k] for k in tags_keys},
            'fields': fields,
            'time': line[time_key],
        }

    columns = [column for (column, _type) in arff_input['attributes']]
    df = pd.DataFrame(arff_input['data'], columns=columns).apply(convert_line, axis=1)
    return line_protocol.make_lines({'points': df})


if __name__ == '__main__':
    parser = ArgumentParser(description='Convert ARFF files to InfluxDB line protocol.')
    parser.add_argument('-i', '--input', default='.', help='folder to be searched for *.arff files')
    parser.add_argument('-o', '--output', default='data.txt', help='output file to write InfluxBD lines to')
    parser.add_argument('-m', '--measurement', help='name of the measurement (e.g. devicemotion)', required=True)
    args = parser.parse_args()

    folder = path.join(args.input, '**', '*.arff')
    print(f'Searching for *.arff files recursively in {args.input}')
    total_row_count = 0

    with open(args.output, 'w') as output:
        for filename in iglob(folder, recursive=True):
            arff_input = read_arff(filename)
            row_count = len(arff_input['data'])
            total_row_count += row_count

            print(f'Processing {row_count} rows in {filename}')
            output.write(arff_to_influxdb(arff_input, measurement=args.measurement) + "\n")

    print(f'Wrote {total_row_count} rows to {args.output}')
