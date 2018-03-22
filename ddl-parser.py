#!/usr/bin/python
import re
from jinja2 import Environment
import datetime
import os.path
import fnmatch
import argparse


def extract_tokens_by_commas(
        text, offset, on_token, separator=',',
        brakets_open='({[',
        brakets_close=')}]',
        ):
    token = ""
    braket_cnt = 1
    while offset < len(text):
        if text[offset] in brakets_open:
            braket_cnt = braket_cnt + 1
        if text[offset] in brakets_close:
            braket_cnt = braket_cnt - 1

        if (braket_cnt == 1 and text[offset] in separator) or braket_cnt == 0:
            on_token(token)
            token = ""
        else:
            token = token + text[offset]

        if braket_cnt == 0:
            break
        offset = offset + 1
    return offset


def parse_constraint_def(token):
    m = re.search(
        '^\s*(?:constraint\s+(\S+)\s*)?'
        '((?:primary\s+key)|(?:unique))\s+'
        '(?:(clustered|nonclustered)\s+)?\((.*?)\)', token, re.I+re.M+re.S)
    if m is None:
        return None
    return {
        'name': m.group(1),
        'type': m.group(2),
        'storage': m.group(3),
        'columns': [x.strip() for x in m.group(4).strip().split(',')]
    }
    pass


def parse_column_def(token):
    m = re.search('^\s*(\S+)\s*(\S+(?:\s*\([^)]+?\))?)\s*(.*)$', token)
    if m is not None:
        return {
            'name': m.group(1),
            'type': m.group(2),
            'extra': m.group(3)
        }
    else:
        return None


def parse_tables(filename):
    data = open(filename, 'rU').read()

    # Remove commentaries
    data = re.sub('^(.*?)(--.*)$', '\\1', data, 0, re.M)
    data = re.sub('\/\*.*?\*\/', '', data, 0, re.M+re.S)
    data = re.sub('\t', ' ', data, 0, re.M)

    tables = {}
    table = {}
    index = {}

    def gather_table_columns(token):
        token = token.strip()
        if token == '':
            return
        constr_def = parse_constraint_def(token)
        if constr_def is not None:
            table['constraints'].append(constr_def)
        else:
            coldef = parse_column_def(token)
            if coldef is not None:
                table['columns'].append(coldef)
        pass

    def gather_index_columns(token):
        token = token.strip()
        if token != '':
            index['columns'].append(token)

    # Parse table structure
    for m in re.finditer(
            '\\bcreate\s+table\s+([^\s()]+)\s*\(', data, re.M+re.S+re.I):
        table_name = m.group(1)
        # Skip temporary tables
        if table_name.startswith('#'):
            continue

        table = {
            "name": table_name,
            "columns": [],
            "indexes": [],
            "constraints": []
        }
        idx = m.end()
        extract_tokens_by_commas(
            data, idx,  on_token=gather_table_columns
        )
        tables[table_name] = table

    # Parse indexes
    for m in re.finditer(
                 '\\bcreate\s+?(?:(clustered|nonclustered|unique)'
                 '\s+)?index\s+(\S+)\s+on\s*(\S+)\s*\(',
                 data, re.M+re.S+re.I):

        table_name = m.group(3)
        index = {
            'name': m.group(2), 'type': m.group(1),
            'columns': []
        }
        extract_tokens_by_commas(data, m.end(), gather_index_columns)
        tables[table_name]['indexes'].append(index)
        pass
    # Parse constraints
    return tables.values()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--file_format',
        default='m_00000_%06d_%s',
        help='default m_00000_%%06d_%%s'
    )
    parser.add_argument(
        '--template',
        default='{{tables|tojson(indent=2)}}'
    )
    parser.add_argument('source_path')
    parser.add_argument('target_path')
    args = parser.parse_args()

    matches = []
    for root, dirnames, filenames in os.walk(args.source_path):
        for filename in fnmatch.filter(filenames, '*.sql'):
            matches.append(os.path.join(root, filename))

    def datetimeformat(value, format='%d-%m-%Y %H:%M'):
        return value.strftime(format)
    env = Environment(trim_blocks=False)
    env.filters['datetimeformat'] = datetimeformat

    if args.template.startswith('@'):
        template = open(args.template[1:], 'rU').read()
    else:
        template = args.template
    tmp = env.from_string(template)
    tmp.globals['now'] = datetime.datetime.now

    count_files = 0

    for filename in matches:
        print 'Processing %s...' % filename
        tables = parse_tables(filename)
        if len(tables) > 0:
            base = os.path.splitext(os.path.basename(filename))
            count_files = count_files + 1
            migration_name = args.file_format % (count_files, base[0])

            converted = tmp.render(
                tables=tables,
                filename=migration_name,
                source=filename
            )
            f = open(
                os.path.join(args.target_path, migration_name+'.php'), 'w'
            )
            f.write(converted)
            f.close()
    pass


if __name__ == '__main__':
    main()
    pass
