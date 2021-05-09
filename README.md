# AmeraShare - Development On-Boarding

AmeraShare is a combination of our ReactJS UI and a Falcon API with a PostgreSQL database backend.

## Requirements

- Docker
- `docker-compose` `1.28.x` or greater
- NodeJS 14
- Yarn

## Repositories

| Repository | Description | Status |
|---|---|---|
|Amera-Iot/web-api|Python backend API.  Owner of `docker-compose` file that runs everything|Active|
|Amera-Iot/web-notifications|NodeJS SSE Server|Deprecating|
|Amera-Iot/web-share|ReactJS UI, proxies to the API|Active|

## docker-compose

There are `docker-compose.yml` files across the different projects, however most are outdated and not being used.  `web-api` contains a `docker-compose.yml` that currently contains the sequence of all the services that encompass all of AmeraShare.  However, not all of them need to be used when doing local development in the API and UI, and are not necessary for day to day development.

This `docker-compose.yml` also contains a sequence of `SQL` files that are necessary to build the development database.

We are currently using `docker-compose` version `1.28.x` or greater.

## Running local development

To run the local development environment you must clone the two following repositories:

- `web-share`
- `web-api`

You can clone `web-notifications` (to be replaced soon).  But they it is of no use and unnecessary, unless you're testing the call notifications.

However, because of the way `docker-compose` works, we do need to have existing directories, even if they are empty or cloned, for the following:

- `web-signaling`
- `web-notifications`

### Running the API

To run the API for which `web-share` depends on, you must run it with `docker-compose` in the `web-api` project, as such:

```shell
docker-compose up -d -- amera-nginx
```

This will start:

- `amera-web-db`
- `amera-web-api`
- `amera-nginx`
- `amera-dns`

`NGINX` is our reverse proxy, and forwards most requests to `amera-web-api`, other services can be hooked in, but that is unnecessary right now.

`docker-compose` will start up the services until they are healthy, and in the following order:

- `amera-dns`
- `amera-web-db`
- `amera-web-api`
- `amera-nginx`

`NGINX` will run on: <http://localhost:9000>

### Running the UI

Running the UI takes place by using `yarn`.  We have a version of `amera-web-share` in `docker-compose`, but it is not recommended as it takes up a lot of resources that are unnecessary and is slow.

Just by running `yarn` to install dependencies, and `yarn start`, will start up the UI.

`yarn` will run the UI on: <http://localhost:3000>

### Amera DNS

The default setup starts a `dnsmasq` service that allows us to access AmeraShare via a `.local` domain, this configures a wildcard DNS for `*.dev.amera.local`, along with this, wildcard SSL certificates, and root authority certificate are in the directory `certs/dev.amera.local.root-ca.pem`.

`NGINX` is already configured to accept `share.dev.amera.local` as a domain using the SSL certificate `certs/wildcard.dev.amera.local.crt`.

`dnsmasq` is currently configured to run on port `5380`.

#### `host.docker.internal` in `docker-compose.yml` - OSX/Windows

To leverage the `NGINX` configuration that sets up `https` with `http2`, there's one line in the `docker-compose.yml` that needs to be commented out, this is specific to OSX/Windows.

In the `amera-nginx` service there's a `network` alias called `host.docker.internal`, if you just comment it out, before starting all the services, this will allow the docker services, to communicate to the host (127.0.0.1) and listen to ports from the host itself.

#### `host.docker.internal` in `docker-compose.yml` - Linux

In linux, there's a different approach stated here: <https://github.com/docker/for-linux/issues/264#issuecomment-823528103>

By adding the following in `docker-compose.yml` for `amera-nginx`:

```yaml
extra_hosts:
    host.docker.internal: host-gateway
```

And then starting up the services

#### `dnsmasq` on OSX

Currently this is where `dnsmasq` works best, as the OSX allows us to create a resolver, with a custom port (in this case `5380`)

To get this working you must first create the file `/etc/resolver/dev.amera.local` with contents:

```text
nameserver 127.0.0.1
port 5380
```

This will communicate your system to add requests for `*.dev.amera.local` to our instance of `dnsmasq` that runs in docker.

### `dnsmasq` on other systems

Linux systems seem to have trouble accepting the custom port for `dnsmasq`, and as such we currently don't have a solution, however, it would be encouraging to do some research to get this working.

Windows, with the use of the WSL2, may support some of this, but we have not found an official solution, though lots of articles on the web are around that

#### Hosts file

If you are unable to get `dnsmasq` working, but want to take advantage of local development with `http2` and `https`, you can manually edit your hosts file:

- Linux/OSX - `/etc/hosts`
- Windows - `C:\Windows\System32\drivers\etc\hosts`

Adding this line at the very end of it:

```text
127.0.0.1   share.dev.amera.local
```

## Loading the UI

Once you point your browser to <http://localhost:3000>, the UI will load, and you can sign in.  It automatically proxies requests from <http://localhost:3000/api> to <http://localhost:9000>.

To sign in, you must use `test@email.com` and `password` as the username/password combination.

Other test accounts are `adrian@email.com`, `adrian2@email.com`, etc.  All with the same password.

## Contacts

By default when the database is started up, there are no contacts for any of the accounts, so you must manually go to AmeraShare users in the contacts section, and add them.

## Issues - Old - Running API locally without docker

Sometimes `psycopg2` will not install due to a SSL Library issue:

If the root of your SSL library installation is `/usr/local/opt/openssl`, then do:

```shell
LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib"
```

By pointing to your installation of openssl, `pipenv` will be able to install

### Bash

```shell
LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib" pipenv install
```

### Fish

```shell
env LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib" pipenv install
```

or

```shell
begin
    set -lx LDFLAGS "-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib"
    pipenv install
end
```

## Environment File

`.env` is the environment file that will beed to be kept up to date with credentials and other secrets:

```shell
# Application

AMERA_API_ENV_NAME=LOCAL
AMERA_API_LOG_LEVEL=DEBUG
AMERA_API_DATABASE.LOG_LEVEL=INFO
AMERA_API_WEB.SESSION_EXPIRATION=31536000

# Application Database
AMERA_API_DATABASE.PASSWORD=

# Third Party Services

## AWS
AMERA_API_SERVICES.AWS.ACCESS_KEY_ID=
AMERA_API_SERVICES.AWS.SECRET_ACCESS_KEY=

## Twilio
AMERA_API_SERVICES.TWILIO.ACCOUNT_SID=
AMERA_API_SERVICES.TWILIO.TWIML_APPLICATION_SID=
AMERA_API_SERVICES.TWILIO.APP_SID=
AMERA_API_SERVICES.TWILIO.AUTH_TOKEN=
AMERA_API_SERVICES.TWILIO.SENDER_NUMBER=
AMERA_API_SERVICES.TWILIO.TEXT_VERIFICATION_MESSAGE="Testing text message."
AMERA_API_SERVICES.TWILIO.API_KEY=
AMERA_API_SERVICES.TWILIO.API_SECRET=

## IPREGISTRY
AMERA_API_SERVICES.IPREGISTRY.API_KEY=

## Rackspace Email SMTP Server
AMERA_API_SMTP.PASSWORD=

## Kafka
AMERA_API_KAFKA.CALLS_TOPIC=calls
AMERA_API_KAFKA.SMS_TOPIC=sms
AMERA_API_KAFKA.EMAIL_TOPIC=email
AMERA_API_KAFKA.CHAT_TOPIC=chat
AMERA_API_KAFKA.CALENDAR_TOPIC=calendar
AMERA_API_KAFKA.SERVER=host.docker.internal:59092,host.docker.internal:59093
AMERA_API_KAFKA.BOOTSTRAP_SERVERS=host.docker.internal:59092,host.docker.internal:59093
AMERA_API_KAFKA.SECURITY.PROTOCOL=ssl

## Github OAuth
AMERA_API_SERVICES.GITHUB.CLIENT_ID=
AMERA_API_SERVICES.GITHUB.CLIENT_SECRET=

## O365
AMERA_API_SERVICES.O365.REFRESH_TOKEN=
AMERA_API_SERVICES.O365.CLIENT_ID=
AMERA_API_SERVICES.O365.CLIENT_SECRET=
AMERA_API_SERVICES.O365.TENANT_ID=

## Trello
AMERA_API_SERVICES.TRELLO.API_KEY=
AMERA_API_SERVICES.TRELLO.SECRET=

```
