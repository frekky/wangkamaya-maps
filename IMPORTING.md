Importing Data
==============

## CSV (for Geonoma)

Initially designed for bulk import of GEONOMA database from CSV format. This is available in various formats via https://catalogue.data.wa.gov.au/dataset/geographic-names-geonoma

You need to know:
- Spatial reference / projection (SRID) of source data
- Which columns in source CSV file map to which fields in the place database

eg.
- `src/manage.py import_csv rawdata/10781_pg4-map-techela_4326.csv --source-desc '10781_map-pg4' --update`

## TXT

Text files are expected to have a specific format, corresponding to the data export of some sort of linguistic database software (possibly Toolbox).

First line of each file is the data description, second line is date of extract, then one or more blank lines.
Records start with the name on one line followed by fields, and are separated by a blank line.
Fields start with `\` and a two-letter field name `xx` and data. Field data may be split across multiple lines.

Sample text file with one record:
```
Martuthunira Place Names
04/05/2020


Yarti
\mr
\ps n
\ge Cane_River
\re Cane River ; River, Cane
\de name of the Cane River
\sd Names and Placenames
\so ADM
\rf
\xv
\xe
\cf Yartira
\nt
\dt 28/Nov/2008
```
