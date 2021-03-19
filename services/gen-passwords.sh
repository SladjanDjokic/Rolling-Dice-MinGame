#!/bin/bash

function generatePassword() {
    openssl rand -hex 16
}

JICOFO_COMPONENT_SECRET=$(generatePassword)
JICOFO_AUTH_PASSWORD=$(generatePassword)
JVB_AUTH_PASSWORD=$(generatePassword)

sed -i.bak \
    -e "s#JICOFO_COMPONENT_SECRET=.*#JICOFO_COMPONENT_SECRET=${JICOFO_COMPONENT_SECRET}#g" \
    -e "s#JICOFO_AUTH_PASSWORD=.*#JICOFO_AUTH_PASSWORD=${JICOFO_AUTH_PASSWORD}#g" \
    -e "s#JVB_AUTH_PASSWORD=.*#JVB_AUTH_PASSWORD=${JVB_AUTH_PASSWORD}#g" \
    "$(dirname "$0")/.env"
