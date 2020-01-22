#!/bin/bash

ORGANIZATION=oneoffcoder
REPOSITORY=dl-transfer
VERSION=0.0.3
IMAGEID=${REPOSITORY}:local

echo ${IMAGEID}

docker tag ${IMAGEID} ${ORGANIZATION}/${REPOSITORY}:${VERSION}
docker tag ${IMAGEID} ${ORGANIZATION}/${REPOSITORY}:latest

docker push ${ORGANIZATION}/${REPOSITORY}:${VERSION}
docker push ${ORGANIZATION}/${REPOSITORY}:latest