#!/usr/bin/python
import re
from jinja2 import Environment
import datetime
import os.path
import fnmatch
import argparse

template = """<?php
/*
    Auto generated {{ now() | datetimeformat }} from {{source}}
*/

class {{ filename }} extends Migration
{
    public function up()
    {
{% for table in tables %}
       $this->createTableIfNotExists('{{ table.name }}',array({% for column in table.columns %}
            '{{column[0]}}' => '{{column[1]}}'{% if not loop.last %},{% endif %}{{""}}{% endfor %}
       ));

{% endfor %}
    }
}
"""


def parse_tables(filename):
    data = open(filename, 'rU').read()

    data = re.sub('^(.*?)(--.*)$', '\\1', data, 0, re.M)
    data = re.sub('\/\*.*?\*\/', '', data, 0, re.M+re.S)
    data = re.sub('\t', ' ', data, 0, re.M)

    tables = []

    for m in re.finditer('create\s+table\s+(\S+)\s*\(', data, re.M+re.S):
        table_name = m.group(1)

        # Skip temporary tables
        if table_name.startswith('#'):
            continue

        idx = m.end()
        brakets = 1

        table_body = []
        column = ""

        while idx < len(data):
            if data[idx] == '(':
                brakets = brakets + 1
            if data[idx] == ')':
                brakets = brakets - 1

            if (brakets == 1 and data[idx] == ',') or brakets == 0:
                column = column.strip()
                if column != "":
                    column = re.sub('\s{2,}', ' ', column)
                    if column.startswith('primary key '):
                        table_body.append([column, ''])
                    else:
                        table_body.append(column.split(' ', 1))
                    column = ""

                if brakets == 0:
                    break
            else:
                column = column + data[idx]
            idx = idx + 1

        # if not table_name.startswith('#'):
        tables.append({'name': table_name, 'columns': table_body})
    return tables


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--file_format',
        default='m_00000_%06d_%s',
        help='default m_00000_%%06d_%%s'
    )
    parser.add_argument('source_path')
    parser.add_argument('target_path')
    args = parser.parse_args()
    print args

    matches = []
    for root, dirnames, filenames in os.walk(args.source_path):
        for filename in fnmatch.filter(filenames, '*.sql'):
            matches.append(os.path.join(root, filename))

    def datetimeformat(value, format='%d-%m-%Y %H:%M'):
        return value.strftime(format)
    env = Environment()
    env.filters['datetimeformat'] = datetimeformat

    tmp = env.from_string(template)
    tmp.globals['now'] = datetime.datetime.utcnow

    count_files = 0

    for filename in matches:
        print filename
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
