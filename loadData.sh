#!/bin/bash

# Variables generales
DATA_DIR="/data/Fragmentos"
CRATEDB_INTERNAL_IP="172.20.0.17"  # Cambia según la IP interna de tu contenedor CrateDB
CRATEDB_EXTERNAL_IP="127.0.0.1"  # IP externa para CrateDB cuando se accede desde fuera
CRATEDB_PORT=4200

# Detectar si se ejecuta dentro de un contenedor
if grep -q "/docker" /proc/1/cgroup; then
    CRATEDB_IP="$CRATEDB_INTERNAL_IP"
else
    CRATEDB_IP="$CRATEDB_EXTERNAL_IP"
fi

# Crear la base de datos en ArangoDB si no existe
create_arangodb_database() {
  local container=$1
  local port=$2

  echo "Creando la base de datos KhaBench en $container (ArangoDB)..."
  docker exec -i $container arangosh \
    --server.endpoint "tcp://127.0.0.1:$port" \
    --server.authentication false \
    --javascript.execute-string "if (!db._databases().includes('KhaBench')) db._createDatabase('KhaBench');"
}

# Cargar datos en ArangoDB
load_arangodb() {
  local container=$1
  local port=$2
  local csv_file=$3
  local collection_name=$4

  echo "Cargando $csv_file en la colección $collection_name de la base de datos KhaBench en $container (ArangoDB)..."
  docker exec -i $container arangoimport \
    --file "$DATA_DIR/$csv_file" \
    --collection "$collection_name" \
    --type "csv" \
    --server.endpoint "tcp://127.0.0.1:$port" \
    --server.database "KhaBench" \
    --server.authentication false \
    --create-collection true
}

# Cargar datos en OrientDB
load_orientdb() {
  local container=$1
  local port=$2
  local json_file=$3

  echo "Cargando datos desde $json_file en la base de datos KhaBench en $container (OrientDB)..."
  docker exec -i $container /orientdb/bin/console.sh <<EOF
CONNECT remote:localhost:$port root rootpwd;
CREATE DATABASE remote:localhost/KhaBench root rootpwd plocal;
CONNECT remote:localhost/KhaBench root rootpwd;
CREATE CLASS MyCollection EXTENDS V; -- Crear la clase como documento
INSERT INTO MyCollection (key, value) VALUES ('example', 'value');
EXIT;
EOF
}

# Cargar datos en CrateDB
# Cargar datos en CrateDB
load_cratedb() {
  local container=$1
  local csv_file=$2
  local table_name=$3

  # Detectar si estamos dentro o fuera del contenedor
  if docker exec -i "$container" bash -c "curl -s http://172.20.0.13:4200/_sql > /dev/null"; then
    CRATEDB_HOST="172.20.0.13"
    CRATEDB_PORT="4200"
  else
    CRATEDB_HOST="127.0.0.1"
    CRATEDB_PORT="4201"
  fi

  echo "Verificando conexión con CrateDB en $CRATEDB_HOST:$CRATEDB_PORT..."
  if ! curl -s "http://$CRATEDB_HOST:$CRATEDB_PORT/_sql" > /dev/null; then
    echo "Error: No se puede conectar a CrateDB en $CRATEDB_HOST:$CRATEDB_PORT. Verifica que el contenedor esté corriendo."
    return
  fi

  echo "Verificando si el archivo $csv_file está disponible en $container..."
  docker exec -i "$container" bash -c "test -f /data/$csv_file"
  if [ $? -ne 0 ]; then
    echo "Error: El archivo $csv_file no existe dentro del contenedor $container."
    return
  fi

  echo "Creando tabla '$table_name' en la base de datos KhaBench en $CRATEDB_HOST:$CRATEDB_PORT..."
  docker exec -i "$container" bash -c "curl -X POST 'http://$CRATEDB_HOST:$CRATEDB_PORT/_sql' \
    -H 'Content-Type: application/json' \
    -d '{\"stmt\":\"CREATE TABLE IF NOT EXISTS $table_name (asin STRING, title STRING, price FLOAT, imgUrl STRING, productId INT, brand INT)\"}'"

  echo "Cargando $csv_file en la tabla $table_name de la base de datos KhaBench en $CRATEDB_HOST:$CRATEDB_PORT..."
  docker exec -i "$container" bash -c "curl -X POST 'http://$CRATEDB_HOST:$CRATEDB_PORT/_sql' \
    -H 'Content-Type: application/json' \
    -d \"{\\\"stmt\\\":\\\"COPY $table_name (asin, title, price, imgUrl, productId, brand) FROM '/data/$csv_file' WITH (format = 'csv', header = true)\\\"}\""
}








# Inicio del proceso de carga
echo "Iniciando carga de datos en la base de datos distribuida KhaBench..."

# Crear bases de datos en los manejadores
create_arangodb_database "arangodb_coordinator1" 7101

# Fragmento 1
load_arangodb "arangodb_coordinator1" 7101 "1/CLIENTES_1.csv" "Clientes"
#load_orientdb "orientdb-node1" 2424 "1/Order.json"
load_cratedb "cratedb-node1" "Fragmentos/1/PRODUCTOS_1.csv" "productos"

echo "Carga de datos finalizada."
