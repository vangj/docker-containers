#!/bin/bash

ORGANIZATION=oneoffcoder
REPOSITORY=dl-classifier
VERSION=0.0.3
IMAGEID=$(docker images | awk -v repo="$REPOSITORY" -v tag="local" 'index($1, repo) && index($2, tag) {print $3}')

echo ${IMAGEID}

docker tag ${IMAGEID} ${ORGANIZATION}/${REPOSITORY}:${VERSION}
docker tag ${IMAGEID} ${ORGANIZATION}/${REPOSITORY}:latest

docker push ${ORGANIZATION}/${REPOSITORY}:${VERSION}
docker push ${ORGANIZATION}/${REPOSITORY}:latest