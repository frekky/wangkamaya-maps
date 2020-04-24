Wangka Maya Aboriginal Place Name Mapping Project
=================================================

Goal: display Aboriginal Australian place names on a Google map.

Place name data comes from various sources, one of which is the Landgate GEONOMA dataset (published on the Landgate website).

Dev Environment Setup <a name="envsetup"></a>
---------------------

- This project uses Python version >= 3.5
- Install packages `apt-get install python3-virtualenv python3-dev build-essential libldap2-dev libsasl2-dev sqlite3`
- `git clone https://gitlab.ucc.asn.au/frekk/uccportal uccportal`
- `cd uccportal`
- `virtualenv env`
- Every time you want to do some uccportal development, do `source env/bin/activate` to set up your environment
- Install python dependencies to local environment: `pip install -r pip-packages.txt`
- Configure django: `cp src/gms/settings_local.example.py src/gms/settings_local.py`
    - Edit `src/gms/settings_local.py` and check that the database backend is configured correctly. (sqlite3 is fine for development)
- Initialise the database: `src/manage.py makemigrations memberdb squarepay && src/manage.py migrate memberdb squarepay`
    - Make sure you run this again if you make any changes to `src/memberdb/models.py` to keep the DB schema in sync.
- Run the local development server with `src/manage.py runserver`


Configuring the database backend
--------------------------------

Using a Linux server (with postgresql installed).

To set up a the database,

```
$ sudo su - postgres
$ psql
postgres=# create database placedb;
postgres=# CREATE USER placedb WITH ENCRYPTED PASSWORD 'insert-password-here';
postgres=# GRANT ALL on DATABASE placedb to placedb;
```

