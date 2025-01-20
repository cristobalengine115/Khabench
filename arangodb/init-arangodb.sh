sudo docker run -e ARANGO_RANDOM_ROOT_PASSWORD=1 -p 8529:8529 -d \
    -v Data:/var/lib/arangodb3 \
    arangodb
