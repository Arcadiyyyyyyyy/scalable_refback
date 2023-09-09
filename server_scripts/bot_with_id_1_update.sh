#!/bin/bash

container_name="refback_bot_with_id_1"
image_location="ghcr.io/arcadiyyyyyyyy/scalable_refback/bot_with_id_1:refs_heads_main"

echo "Started stopping the "+$container_name+" container"

docker stop $container_name
docker rm $container_name
docker pull $image_location
docker run --name=$container_name -d --env-file=prod.env --network=host $image_location
docker rmi -f "$(docker images -aq -f "dangling=true")"

echo "Restarted "+$container_name
