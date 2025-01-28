
import os
import requests

# Configuración de nodos y carpetas
nodes = {
    "1": "http://localhost:4201/_sql",
    "2": "http://localhost:4202/_sql",
    "3": "http://localhost:4203/_sql"
}

fragment_base_path = "./data/Fragmentos"

def create_cratedb_database(node_url, database):
    print(f"Creando/verificando esquema {database} en CrateDB ({node_url})...")
    response = requests.post(node_url, json={"stmt": f"CREATE SCHEMA {database}"})
    if response.status_code == 200:
        print(f"Esquema {database} creado exitosamente en CrateDB ({node_url}).")
    elif "SQLParseException" in response.text:
        print(f"Esquema {database} ya existe en CrateDB ({node_url}).")
    else:
        print(f"Error al crear el esquema {database} en CrateDB: {response.text}")

def load_to_cratedb(node_url, file_path, table_name):
    with open(file_path, 'r') as file:
        data = file.read()
    query = f"COPY {table_name} FROM STDIN WITH (format csv, delimiter ',', null '\\N')"
    response = requests.post(node_url, json={"stmt": query, "bulk_args": data})
    if response.status_code == 200:
        print(f"Datos cargados a {table_name} en CrateDB correctamente desde {file_path}.")
    else:
        print(f"Error al cargar datos en CrateDB: {response.text}")

def process_crate_fragments():
    for fragment_id, node_url in nodes.items():
        fragment_path = os.path.join(fragment_base_path, fragment_id)
        if not os.path.exists(fragment_path):
            print(f"Carpeta {fragment_path} no encontrada. Skipping...")
            continue

        create_cratedb_database(node_url, "khabench")

        for root, _, files in os.walk(fragment_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file.startswith("CLIENTES"):
                    load_to_cratedb(node_url, file_path, "khabench.clientes")
                elif file.startswith("PRODUCTOS"):
                    load_to_cratedb(node_url, file_path, "khabench.productos")
                else:
                    print(f"Archivo {file} no reconocido para carga automática en CrateDB.")

if __name__ == "__main__":
    process_crate_fragments()
