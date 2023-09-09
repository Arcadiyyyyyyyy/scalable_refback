#!/bin/bash

container_name="refback_api"
image_location="ghcr.io/arcadiyyyyyyyy/scalable_refback/refback_api:refs_heads_main"

echo "Started stopping the api container"

docker stop $container_name
docker rm $container_name
docker pull $image_location
docker run --name=$container_name -d --env-file=prod.env -p 8000:80 $image_location
docker rmi -f "$(docker images -aq -f "dangling=true")"

echo "Restarted api!"