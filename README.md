Wangka Maya Aboriginal Place Name Mapping Project
=================================================

Goal: display Aboriginal Australian place names on a Google map.

Place name data comes from various sources, one of which is the Landgate GEONOMA dataset (published on the Landgate website).

All spatial data is stored in the database using spatial reference WGS84 (SRID ESRI:4326) for compatability with Google Maps.

Designed as a potential sort-of-extension for the Discovery Song database with a focus on mapping and storing geographical data.

Installation
------------

These instructions outline installation on a Linux system (eg. Debian or Ubuntu).

- This project uses Python version >= 3.5, PostgreSQL with PostGIS, and the GDAL library.
- Install packages `apt-get -y install git python3-virtualenv python3-dev build-essential postgresql postgresql-10-postgis-2.4 postgresql-server-dev-10 gdal-bin libgdal20 libgdal-dev libgeos-dev libgeos-3.6.2 python3-gdal proj-bin libproj-dev`
- `git clone https://bitbucket.org/Javacow/wm-maps.git placedb`
- `python3 -m virtualenv -p $(which python3) pyenv`
- `cd placedb`
- Run `source ../pyenv/bin/activate` to set up your environment
- Install python dependencies to local environment: `pip install django psycopg2 postgis geos `
- Configure the database, see section below.
- Check you have a Google Maps API key on hand. If you don't have one, follow the instructions [here](https://developers.google.com/maps/documentation/javascript/get-api-key).
- Configure Django:
    - Edit `src/placesdb/settings.py`, the options are commented with what they do
    - Make sure to set SECURITY_KEY to something random
    - Check that ALLOWED_HOSTS contains at least the DNS hostname of the server which people will connect to
    - Check that the DEBUG setting is correct (ie. False for production deployments)
    - Update Database settings
    - Set log file path correctly, ensure the location is writable by your user (or the Apache user for production)
- Edit `src/templates/map.html` and put your API key into the Google Maps javascript URL
- Initialise the database: `src/manage.py makemigrations && src/manage.py migrate`
- Follow steps below, depending whether you are setting up for development or production

### Development environment
- Run the local development server with `src/manage.py runserver`
- That's it, you can connect to the built-in django webserver and test stuff


### Production
This guide uses Apache 2.4 and mod_wsgi with Python 3. Don't install to a system if there is already an app using Apache/mod_wsgi with Python 2, it is incompatible and you WILL break it.

1. Install some packages: `apt-get -y install apache2 libapache2-mod-wsgi-py3`
2. Navigate to the directory where you checked out the repository. Let's assume that was `/home/placedb/placedb-git`
3. Copy the following into `/etc/apache2/sites-available/placedb.conf`, updating email addresses, paths and domain names where applicable:

```
<VirtualHost *:443>
    ServerAdmin admin@wangkamaya.org.au
    ServerName maps.wangkamaya.org.au
    #ServerAlias (other domain names here, repeat line for more)

    DocumentRoot /home/placedb/placedb-git/static

    <Directory /services/uccportal/wwwroot>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>

    WSGIDaemonProcess placedb python-home=/home/placedb/pyenv python-path=/home/placedb/placedb-git/src
    WSGIProcessGroup placedb
    WSGIScriptAlias / /home/placedb/placedb-git/placesdb/wsgi.py

    <Directory /home/placedb/placedb-git/placesdb>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>

    Protocols h2 http:/1.1

    <Directory /home/placedb/placedb-git/static>
        Require all granted
    </Directory>

    Alias /static /home/placedb/placedb-git/static

    #SSLEngine On
    #SSLCertificateFile /etc/letsencrypt/live/.../cert.pem
    #SSLCertificateKeyFile /etc/letsencrypt/live/.../privkey.pem
    #SSLCertificateChainFile /etc/letsencrypt/live/.../chain.pem

    ErrorLog ${APACHE_LOG_DIR}/placedb/error.log
    CustomLog ${APACHE_LOG_DIR}/placedb/access.log combined
</VirtualHost>

```

4. Collect the django static files into the location served by apache:
	- `src/manage.py collectstatic`
	
5. Set permissions (run as root)
	- `mkdir -p /home/placedb/logs`
	- `chown -R root:www-data /home/placedb && chmod 640 /home/placedb`
	- `chmod 610 /home/placedb/logs`

Configuring the database backend
--------------------------------

Using a Linux server (with postgresql installed).

To set up a the database,

```
$ sudo su - postgres
$ createdb placedb
$ psql placedb
postgres=# CREATE USER placedb WITH ENCRYPTED PASSWORD 'insert-password-here';
postgres=# GRANT ALL on DATABASE placedb to placedb;
postgres=# CREATE EXTENSION postgis;

```

References
==========

von Brandenstein, C. G. (1973). Place Names of the North-West. *The Western Australian Naturalist*, 12(5), 97-107.
