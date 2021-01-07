import csv
import itertools
import logging

from .dataset import Dataset

logger = logging.getLogger(__name__)

def get_csv_dialect(f):
    # use the first chunk to deduce the format
    chunk = next(iter(f))
    csv.Sniffer().sniff(chunk)

def wrap_file_str(file):
    # wrap the file object in a generator to ensure we feed only strings to the CSV reader
    str_f = file
    file.seek(0)
    for line in file:
        if type(line) == str:
            logger.debug('iterating file object produces str')
        elif type(line) == bytes:
            str_f = (line.decode('utf-8') for line in file)
            logger.debug('iterating file object produces bytes, convert to str')
        else:
            logger.warning('iterating file object produces unexpected data type=%s' % type(line))
    return str_f

def get_csv_info(file, leave_open=True):
    try:
        f = file.open('r')
        dialect = get_csv_dialect(wrap_file_str(f))

        reader = csv.reader(wrap_file_str(f), dialect)
        fields = next(reader)
        num_rows = 0
        num_weird_rows = 0
        for row in reader:
            num_rows += 1
            if len(row) != len(fields):
                num_weird_rows += 1
        return (fields, num_rows, num_weird_rows)
    finally:
        if not leave_open:
            f.close()
    

def import_csv_with_colmap(csvfile, colmap, source):
    with csvfile.open('r') as f:
        dialect = get_csv_dialect(wrap_file_str(f))
        reader = csv.DictReader(wrap_file_str(f), dialect)
        
        ds = Dataset(colmap)
        return ds.bulk_ingest(reader, source, batch_size=50, allow_update=True)