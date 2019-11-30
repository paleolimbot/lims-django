
# A Docker dev environment

This replaces the [python](https://www.python.org/) dependency with [Docker](https://docs.docker.com/install/)
and [Compose](https://docs.docker.com/compose/install/).

In this `docker-dev` directory commands can be run via docker. Docker will download and build a 
development image the first time you bring up the container.

## Setup

```bash
docker-compose run --rm lims migrate
docker-compose run --rm lims createsuperuser
docker-compose run --rm lims shell --command="from lims.tests import populate_test_data; populate_test_data()"
```

## Run a server

```bash
docker-compose up
```
