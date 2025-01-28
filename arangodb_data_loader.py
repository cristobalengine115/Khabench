import os
import requests
import json
import csv

# Configuración de nodos y carpetas
coordinators = {
    "1": "http://localhost:7101",
    "2": "http://localhost:7102",
    "3": "http://localhost:7101"  # Ajustado para incluir el fragmento 3
}

fragment_base_path = "./data/Fragmentos"

def csv_to_json(file_path, shard_key_value):
    """Convierte un archivo CSV en una lista de objetos JSON, con soporte para delimitadores personalizados."""
    data = []
    delimiter = '|' if 'RESEÑAS' in file_path else ','  # Maneja el delimitador especial para RESEÑAS
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=delimiter)
        for row in reader:
            row['fragment_id'] = shard_key_value  # Agregar el campo de sharding
            data.append(row)
    return data

def create_arangodb_database(coordinator_url, database):
    """Crea una base de datos en ArangoDB si no existe."""
    print(f"Creando/verificando base de datos {database} en ArangoDB ({coordinator_url})...")
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{coordinator_url}/_api/database", headers=headers, data=json.dumps({"name": database}))
    if response.status_code == 201:
        print(f"Base de datos {database} creada exitosamente en ArangoDB ({coordinator_url}).")
    elif response.status_code == 409:
        print(f"Base de datos {database} ya existe en ArangoDB ({coordinator_url}).")
    else:
        print(f"Error al crear la base de datos {database} en ArangoDB: {response.text}")

def create_arangodb_collection(coordinator_url, collection_name, shard_key="fragment_id"):
    """Crea una colección en ArangoDB con sharding configurado."""
    print(f"Verificando/creando colección {collection_name} en ArangoDB ({coordinator_url})...")
    headers = {"Content-Type": "application/json"}
    collection_config = {
        "name": collection_name,
        "type": 2,  # Colección de documentos
        "shardKeys": [shard_key],
        "numberOfShards": 3  # Número de shards (uno por dbserver)
    }
    response = requests.post(f"{coordinator_url}/_api/collection", headers=headers, data=json.dumps(collection_config))
    if response.status_code == 200:
        print(f"Colección {collection_name} creada exitosamente en ArangoDB ({coordinator_url}). (status: {response.status_code})")
    elif response.status_code == 409:
        print(f"Colección {collection_name} ya existe en ArangoDB ({coordinator_url}). (status: {response.status_code})")
    else:
        print(f"Error al crear la colección {collection_name} en ArangoDB: {response.text} (status: {response.status_code})")

def load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value):
    """Carga datos a ArangoDB usando la API REST con shard key explícita."""
    headers = {"Content-Type": "application/json"}
    data = []
    if file_path.endswith('.csv'):
        data = csv_to_json(file_path, shard_key_value)
    else:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue  # Omitir líneas vacías
                try:
                    document = json.loads(line)
                    document["fragment_id"] = shard_key_value  # Agregar la clave de shard
                    data.append(document)
                except json.JSONDecodeError as e:
                    print(f"Error de JSON en {file_path}: {e}. Línea omitida.")
    for document in data:
        response = requests.post(f"{coordinator_url}/_api/document/{collection_name}",
                                 headers=headers,
                                 data=json.dumps(document))
        if response.status_code == 201:
            print(f"Documento insertado en {collection_name}: {response.json()}. (shard_key: {document.get('fragment_id')})")
        elif response.status_code == 202:
            print(f"Solicitud aceptada para {collection_name}: {response.json()} (shard_key: {document.get('fragment_id')})")
        else:
            print(f"Error al insertar en ArangoDB: {response.text} (status: {response.status_code}, shard_key: {document.get('fragment_id')})")

def process_arango_fragments():
    """Procesa y carga todos los fragmentos en ArangoDB."""
    for fragment_id, coordinator_url in coordinators.items():
        fragment_path = os.path.join(fragment_base_path, fragment_id)
        if not os.path.exists(fragment_path):
            print(f"Carpeta {fragment_path} no encontrada. Skipping...")
            continue

        create_arangodb_database(coordinator_url, "khabench")

        print(f"Cargando datos del fragmento {fragment_id} a través del coordinador {coordinator_url}...")

        for root, _, files in os.walk(fragment_path):
            for file in files:
                file = file.split(":")[0]  # Limpiar nombres como 'file.csv:Zone.Identifier'
                file_path = os.path.join(root, file)
                if file.startswith("RESEÑAS"):
                    collection_name = f"resenas"
                    create_arangodb_collection(coordinator_url, collection_name)
                    load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value=fragment_id)
                elif file.startswith("CLIENTES"):
                    collection_name = f"clientes"
                    create_arangodb_collection(coordinator_url, collection_name)
                    load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value=fragment_id)
                elif file.startswith("PRODUCTOS"):
                    collection_name = f"productos"
                    create_arangodb_collection(coordinator_url, collection_name)
                    load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value=fragment_id)
                elif file.startswith("order.json"):
                    collection_name = "order"
                    create_arangodb_collection(coordinator_url, collection_name)
                    load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value=fragment_id)
                elif file.startswith("person_hasInterest_tag_0_0.csv"):
                    collection_name = "person_hasInterest_tag"
                    create_arangodb_collection(coordinator_url, collection_name)
                    load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value=fragment_id)
                elif file.startswith("person_knows_person_0_0.csv"):
                    collection_name = "person_knows_person"
                    create_arangodb_collection(coordinator_url, collection_name)
                    load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value=fragment_id)
                elif file.startswith("post_0_0.csv"):
                    collection_name = "post"
                    create_arangodb_collection(coordinator_url, collection_name)
                    load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value=fragment_id)
                elif file.startswith("post_hasCreator_person_0_0.csv"):
                    collection_name = "post_hasCreator_person"
                    create_arangodb_collection(coordinator_url, collection_name)
                    load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value=fragment_id)
                elif file.startswith("post_hasTag_tag_0_0.csv"):
                    collection_name = "post_hasTag_tag"
                    create_arangodb_collection(coordinator_url, collection_name)
                    load_to_arangodb(coordinator_url, collection_name, file_path, shard_key_value=fragment_id)
                else:
                    print(f"Archivo {file} no reconocido para carga automática en ArangoDB.")

if __name__ == "__main__":
    process_arango_fragments()
