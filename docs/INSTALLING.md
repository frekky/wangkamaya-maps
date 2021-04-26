# PlaceDB Installation

These instructions outline installation on a Linux system (eg. Debian or Ubuntu). Windows is not currently supported (although it should not be hard to do).

- This project uses Python version >= 3.5, PostgreSQL with PostGIS, and the GDAL library.
- Install packages `apt-get -y install git python3-virtualenv python3-dev build-essential postgresql postgresql-10-postgis-2.4 postgresql-server-dev-10 gdal-bin libgdal20 libgdal-dev libgeos-dev libgeos-3.6.2 python3-gdal proj-bin libproj-dev`
- `git clone https://bitbucket.org/Javacow/wm-maps.git placedb`
- `python3 -m virtualenv -p $(which python3) pyenv`
- `cd placedb`
- Run `source ../pyenv/bin/activate` to set up your environment
- Install Pip packages: `pip install -r pip-packages.txt`
- Configure the database, see section below.
- Check you have a Google Maps API key on hand. If you don't have one, follow the instructions [here](https://developers.google.com/maps/documentation/javascript/get-api-key).
- Configure Django:
    - Edit `src/placesdb/settings.py`, the options are commented with what they do
    - Make sure to set SECURITY_KEY to something random
    - Check that ALLOWED_HOSTS contains at least the DNS hostname of the server which people will connect to
    - Check that the DEBUG setting is correct (ie. False for production deployments)
    - Update Database settings
    - Set log file path correctly, ensure the location is writable by your user (or the Apache user for production)
- Initialise the database: `src/manage.py makemigrations && src/manage.py migrate`
- Follow steps below, depending whether you are setting up for development or production

### Development environment
- Run the local development server with `src/manage.py runserver`
- That's it, you can connect to the built-in django webserver and test stuff
- Install/upgrade python dependencies to local environment: `pip install --upgrade django psycopg2 postgis pillow geos geojson django-admin-action-buttons pandas django-colorfield`
- Update package list for deployment: `pip freeze > pip-packages.txt`

### Production
This guide uses Apache 2.4 and mod_wsgi with Python 3. Don't install to a system if there is already an app using Apache/mod_wsgi with Python 2, it is incompatible and you WILL break it.

1. Install some packages: `apt-get -y install apache2 libapache2-mod-wsgi-py3 certbot python3-certbot-apache`
2. Navigate to the directory where you checked out the repository. Let's assume that was `/home/placedb/placedb-git`
3. Copy the following into `/etc/apache2/sites-available/placedb.conf`, updating email addresses, paths and domain names where applicable:

```
WSGIDaemonProcess placedb python-home=/home/placedb/pyenv python-path=/home/placedb/placedb-git/src

<VirtualHost *:80>
    ServerAdmin admin@wangkamaya.org.au
    ServerName maps.wangkamaya.org.au
    #ServerAlias (other domain names here, repeat line for more)

    DocumentRoot /home/placedb/wwwroot

    WSGIProcessGroup placedb
    WSGIScriptAlias / /home/placedb/placedb-git/src/placesdb/wsgi.py

    <Directory /home/placedb/placedb-git/src/placesdb>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>

    Protocols h2 http:/1.1

    <Directory /home/placedb/placedb-git/static>
        Require all granted
    </Directory>

    Alias /static /home/placedb/placedb-git/static
    Alias /favicon.ico /home/placedb/placedb-git/static/favicon.ico

    ErrorLog ${APACHE_LOG_DIR}/placedb/error.log
    CustomLog ${APACHE_LOG_DIR}/placedb/access.log combined
</VirtualHost>

```

4. Collect the django static files into the location served by apache:
    - `src/manage.py collectstatic`

5. Set permissions (run as root)

```
mkdir -p /home/placedb/logs /home/placedb/wwwroot /home/placedb/placedb-git/media_uploads && mkdir -p /var/log/apache2/placedb
chown -R root:www-data /home/placedb
chmod -R u=rwX,g=rX,o=rX /home/placedb
chmod -R u=rwX,g=rwX,o=rX /home/placedb/placedb-git/media_uploads
chmod -R u=rwX,g=rwX,o=rX /home/placedb/logs
```

6. Reload web server
    - `a2ensite placedb`
    - `systemctl reload apache2`
    
7. Check that the site works.

8. Enable SSL using LetsEncrypt: (if this succeeds, it should *just work*)
    - `certbot --apache`
    - Follow the instructions at the prompt.
    - This will create a second configuration file at `/etc/apache2/sites-available/placedb-le-ssl.conf` and add a systemctl timer to renew the SSL certificates automatically.

Updating Sources
----------------

To update a production system to the latest git version, login as root.

```
cd /home/placedb/placedb-git
source ../pyenv/bin/activate
git pull
src/manage.py collectstatic -c
src/manage.py check
```

Then run steps 5 and 6 from above to fix the permissions and reload the config.

Configuring the database backend
--------------------------------

Using a Linux server (with postgresql installed).

To set up a the database,

```
sudo su - postgres
createdb placedb
psql placedb
# displays prompt postgres=# 
CREATE USER placedb WITH ENCRYPTED PASSWORD 'insert-password-here';
GRANT ALL on DATABASE placedb to placedb;
CREATE EXTENSION postgis;
CREATE EXTENSION citext;
```

Then log in as www-data to configure django: `sudo su - www-data -s /bin/bash`:

```
cd /home/placedb/placedb-git
source ../pyenv/bin/activate
src/manage.py migrate
```
