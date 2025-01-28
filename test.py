import os
import requests
import json
import csv
import base64

# Configuración de nodos y carpetas
nodes = {
    "1": {
        "crate": "http://localhost:4201/_sql",
        "arango": "http://localhost:7101/_db/_system",
        "orient": "http://localhost:2480"
    },
    "2": {
        "crate": "http://localhost:4202/_sql",
        "arango": "http://localhost:7102/_db/_system",
        "orient": "http://localhost:2481"
    },
    "3": {
        "crate": "http://localhost:4203/_sql",
        "arango": "http://localhost:7103/_db/_system",
        "orient": "http://localhost:2482"
    }
}

# Credenciales para OrientDB
orientdb_user = "root"
orientdb_password = "rootpwd"
orientdb_auth_header = base64.b64encode(f"{orientdb_user}:{orientdb_password}".encode()).decode()
orientdb_headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {orientdb_auth_header}"
}

fragment_base_path = "./data/Fragmentos"

def csv_to_json(file_path):
    """Convierte un archivo CSV a una lista de objetos JSON."""
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]

def ensure_orientdb_class(node_url, database, class_name):
    """Verifica y crea una clase en OrientDB si no existe."""
    response = requests.post(
        f"{node_url}/command/{database}/sql",
        headers=orientdb_headers,
        data=json.dumps({"command": f"SELECT FROM (SELECT expand(classes) FROM metadata:schema) WHERE name = '{class_name}'"})
    )
    if response.status_code == 200 and response.json().get("result"):
        print(f"Clase {class_name} ya existe en OrientDB.")
    else:
        response = requests.post(
            f"{node_url}/command/{database}/sql",
            headers=orientdb_headers,
            data=json.dumps({"command": f"CREATE CLASS {class_name} EXTENDS V"})
        )
        if response.status_code == 200:
            print(f"Clase {class_name} creada exitosamente en OrientDB.")
        else:
            print(f"Error al crear la clase {class_name} en OrientDB: {response.text}")

def create_orientdb_database(node_url, database):
    """Verifica y crea la base de datos en OrientDB si no existe."""
    print(f"Creando/verificando base de datos {database} en OrientDB...")
    response = requests.post(f"{node_url}/database/{database}/plocal", headers=orientdb_headers)
    if response.status_code == 200:
        print(f"Base de datos {database} creada exitosamente en OrientDB.")
    elif response.status_code == 409:
        print(f"Base de datos {database} ya existe en OrientDB.")
    else:
        print(f"Error al crear la base de datos {database} en OrientDB: {response.text}")

def create_arangodb_database(node_url, database):
    """Crea una base de datos en ArangoDB si no existe."""
    print(f"Creando/verificando base de datos {database} en ArangoDB...")
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{node_url}/_api/database", headers=headers, data=json.dumps({"name": database}))
    if response.status_code == 201:
        print(f"Base de datos {database} creada exitosamente en ArangoDB.")
    elif response.status_code == 409:
        print(f"Base de datos {database} ya existe en ArangoDB.")
    else:
        print(f"Error al crear la base de datos {database} en ArangoDB: {response.text}")

def create_arangodb_collection(node_url, collection_name):
    """Crea una colección en ArangoDB si no existe."""
    print(f"Verificando/creando colección {collection_name} en ArangoDB...")
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{node_url}/_api/collection", headers=headers, data=json.dumps({"name": collection_name}))
    if response.status_code == 200:
        print(f"Colección {collection_name} creada exitosamente en ArangoDB.")
    elif response.status_code == 409:
        print(f"Colección {collection_name} ya existe en ArangoDB.")
    else:
        print(f"Error al crear la colección {collection_name} en ArangoDB: {response.text}")

def create_cratedb_database(node_url, database):
    """Crea un esquema en CrateDB para emular la creación de una base de datos."""
    print(f"Creando/verificando esquema {database} en CrateDB...")
    response = requests.post(node_url, json={"stmt": f"CREATE SCHEMA {database}"})
    if response.status_code == 200:
        print(f"Esquema {database} creado exitosamente en CrateDB.")
    elif "SQLParseException" in response.text:
        print(f"Esquema {database} ya existe en CrateDB.")
    else:
        print(f"Error al crear el esquema {database} en CrateDB: {response.text}")

def load_to_cratedb(node_url, file_path, table_name):
    """Carga datos a CrateDB usando COPY."""
    with open(file_path, 'r') as file:
        data = file.read()
    query = f"COPY {table_name} FROM STDIN WITH (format csv, delimiter ',', null '\\\\N')"
    response = requests.post(node_url, json={"stmt": query, "bulk_args": data})
    if response.status_code == 200:
        print(f"Datos cargados a {table_name} en CrateDB correctamente desde {file_path}.")
    else:
        print(f"Error al cargar datos en CrateDB: {response.text}")

def load_to_orientdb(node_url, database, file_path, class_name):
    """Carga datos a OrientDB usando la API REST."""
    ensure_orientdb_class(node_url, database, class_name)
    if file_path.endswith('.csv'):
        data = csv_to_json(file_path)
    else:
        with open(file_path, 'r') as file:
            data = [json.loads(line.strip()) for line in file if line.strip()]
    for document in data:
        response = requests.post(f"{node_url}/command/{database}/sql",
                                 headers=orientdb_headers,
                                 data=json.dumps({"command": f"INSERT INTO {class_name} CONTENT {json.dumps(document)}"}))
        if response.status_code == 200:
            print(f"Documento insertado en {class_name} en OrientDB.")
        else:
            print(f"Error al insertar en OrientDB: {response.text} (status: {response.status_code})")

def load_to_arangodb(node_url, collection_name, file_path):
    """Carga datos a ArangoDB usando la API REST."""
    headers = {"Content-Type": "application/json"}
    create_arangodb_collection(node_url, collection_name)
    if file_path.endswith('.csv'):
        data = csv_to_json(file_path)
    else:
        with open(file_path, 'r') as file:
            data = [json.loads(line.strip()) for line in file if line.strip()]
    for document in data:
        response = requests.post(f"{node_url}/_api/document/{collection_name}",
                                 headers=headers,
                                 data=json.dumps(document))
        if response.status_code == 201:
            print(f"Documento insertado en {collection_name}: {response.json()}.")
        elif response.status_code == 202:
            print(f"Solicitud aceptada para {collection_name}: {response.json()}")
        else:
            print(f"Error al insertar en ArangoDB: {response.text} (status: {response.status_code})")

def process_fragments():
    """Procesa y carga todos los fragmentos en los nodos correspondientes."""
    for fragment_id, urls in nodes.items():
        fragment_path = os.path.join(fragment_base_path, fragment_id)
        if not os.path.exists(fragment_path):
            print(f"Carpeta {fragment_path} no encontrada. Skipping...")
            continue
        create_orientdb_database(urls["orient"], "khabench")
        create_arangodb_database(urls["arango"], "khabench")
        create_cratedb_database(urls["crate"], "khabench")
        for root, _, files in os.walk(fragment_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file.startswith("CLIENTES"):
                    load_to_cratedb(urls["crate"], file_path, "khabench.clientes")
                elif file.startswith("PRODUCTOS"):
                    load_to_cratedb(urls["crate"], file_path, "khabench.productos")
                elif file.startswith("RESEÑAS"):
                    load_to_arangodb(urls["arango"], "resenas", file_path)
                elif file.startswith("USUARIOS"):
                    load_to_arangodb(urls["arango"], "usuarios", file_path)
                elif file.startswith("ORDENES"):
                    load_to_orientdb(urls["orient"], "khabench", file_path, "Ordenes")
                elif file.startswith("post_hasCreator_person"):
                    load_to_orientdb(urls["orient"], "khabench", file_path, "HasCreator")
                else:
                    print(f"Archivo {file} no reconocido para carga automática.")

if __name__ == "__main__":
    process_fragments()
