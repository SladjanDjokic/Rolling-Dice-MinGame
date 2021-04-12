# Clearing volume for new dependency

When installing/upgrading/pinning a dependency version, the way that `amera-web-api` works is that it installs dependencies in a `docker volume`.

This `docker volume` needs to be updated with the new dependency so that the `amera-web-api` code runs as expected.

## Removing `docker volume` (Easiest)

One of the easiest/slowest ways of dealing with `Pipfile` updates is to do the following from the `web-api` directory:

```shell
docker-compose down
```

This will ensure no containers are running, specifically `amera-web-api`.

Then we remove the volume:

```shell
docker volume rm amera-web-api-python-packages
```

This will remove the volume, and force a re-install of dependencies.

```shell
docker-compose up -d -- amera-nginx
```

To start everything back up.  You can watch the `pipenv install` by running:

```shell
docker-compose logs -f --tail=10 amera-web-api
```

_**Note:** This will take a while (5-10 minutes)_

## While `amera-web-api` is still running (Intermediate)

If you're installing a new dependency, or want to manually install an updated dependency, you can shell login to the container:

```shell
docker exec -it amera-web-api bash
```

This will start up an interactive `bash` shell in the container.

_**Note:** This will not work if the container is constantly restarting_

You can then run:

```shell
pipenv install
```

or for a specific package:

```shell
pipenv install <package-name>
```

This will also update `Pipfile` as needed.

## Container restarting (Expert)

If the container is restarting due to an updated `Pipfile` and a module not being found, you can either do the first step, else you can do the following:

```shell
docker-compose down
```

To ensure that all containers are stopped and removed, then modify `docker-compose.yml` to change the `amera-web-api` `command:` to `yes`:

```diff
-command: ["pipenv", "run", "local"]
+command: ["yes"]
```

This will keep the container running once it starts, and won't run the python API application:

```shell
docker-compose up -d -- amera-web-api
```

To start the containers, after:

```shell
docker exec -it amera-web-api bash
```

To log into the container itself, and then you can run:

```shell
pipenv install
```

This will update the volume without having to delete it from the beginning.  

Once this is done, you can then do:

```shell
docker-compose down
```

To bring everything down again, then modify `docker-compose.yml` again:

```diff
-command: ["yes"]
+command: ["pipenv", "run", "local"]
```

After that last modification you can then run:

```shell
docker-compose up -d -- amera-nginx
```

