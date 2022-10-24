import json
from configparser import ConfigParser
from typing import Any, List, Tuple, Union

import psycopg2
from cardanopythonlib import base
from psycopg2.extras import Json

config_path = './config.ini'
def config(config_path: str, section: str) -> dict:
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(config_path)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, config_path))

    return db

def connect() -> None:
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
        params = config(config_path, section='postgresql')

        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)
        # create a cursor
        cur = conn.cursor()
        # execute a statement
        print('PostgreSQL database version:')
        cur.execute('SELECT version()')

        # display the PostgreSQL database server version
        db_version = cur.fetchone()
        print(db_version)
        # close the communication with the PostgreSQL
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')

def create_tables() -> None:
    """ create tables in the PostgreSQL database"""
    commands = (
        """
            CREATE TABLE IF NOT EXISTS wallet (
                id uuid DEFAULT gen_random_uuid (),
                name TEXT,
                base_addr TEXT,
                payment_addr TEXT,
                payment_skey JSON,
                payment_vkey JSON,
                stake_addr TEXT,
                stake_skey JSON,
                stake_vkey JSON,
                hash_verification_key TEXT,
                PRIMARY KEY (id)
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT,
                id_wallet UUID,
                submission TIMESTAMPTZ DEFAULT Now(),
                address_origin TEXT,
                address_destin TEXT,
                tx_cborhex JSON,
                metadata JSON,
                fees BIGINT,
                network TEXT,
                processed BOOLEAN,
                PRIMARY KEY (id),
                FOREIGN KEY (id_wallet)
                    REFERENCES wallet (id)
                    ON UPDATE CASCADE ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS scripts (
                id uuid DEFAULT gen_random_uuid (),
                name TEXT,
                purpose script_purpose,
                content JSON, 
                PRIMARY KEY (id)
            );
            CREATE TABLE IF NOT EXISTS users (
                id uuid DEFAULT gen_random_uuid (),
                id_wallet UUID,
                username TEXT,
                password TEXT,
                is_verified BOOLEAN,
                PRIMARY KEY (id),
                FOREIGN KEY (id_wallet)
                    REFERENCES wallet (id)
                    ON UPDATE CASCADE ON DELETE CASCADE
            );

        """,)
    conn = None
    try:
        # read the connection parameters
        params = config(config_path, section='postgresql')
        # connect to the PostgreSQL server
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        # create table one by one
        for command in commands:
            cur.execute(command)
        # close communication with the PostgreSQL database server
        cur.close()
        # commit the changes
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

def read_query(command: str) -> List:
    
    conn = None
    result = []
    try:
        # read the connection parameters
        params = config(config_path, section='postgresql')
        # connect to the PostgreSQL server
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        # create table one by one
        cur.execute(command)
        # close communication with the PostgreSQL database server
        result = cur.fetchall()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return result

def insert(tableName: str, columns: list[str], values: list) -> Union[int, None]:
    values_q = []
    for value in values:
        if type(value) == str:
            value = value.replace("'", "''")
            value = "'" + value + "'"
        if type(value) == dict:
            value = Json(value)
        if value == None:
            value = 'NULL'
        values_q += [str(value)]
    query = f"INSERT INTO {tableName}"
    query += "(" + ", ".join(columns) + ")\nVALUES"
    query += "(" + ", ".join(values_q) + "), \n"
    query = query[:-3] + " RETURNING id;"
    conn = None
    id = 0
    try:
        # read the connection parameters
        params = config(config_path, section='postgresql')
        # connect to the PostgreSQL server
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        # create table one by one
        cur.execute(query)
        result = cur.fetchone()
        if result is not None:
            id = result[0]
        conn.commit()
        print ('\nfinished CREATE OR INSERT TABLES execution')
        cur.close()
        return id
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        if conn is not None:
            conn.rollback()
        return None
    finally:
        if conn is not None:
            conn.close()

def insert_wallet(wallet_name: str, key_created: dict, key_save_flag: bool) -> dict:

    # Build query
    tableName = 'wallet'
    insert_dict = {}
    if key_save_flag:
        insert_dict['name'] = wallet_name
        insert_dict['base_addr'] = key_created.get("base_addr")
        insert_dict['payment_addr'] = key_created.get("payment_addr")
        insert_dict['payment_skey'] = key_created.get("payment_skey")
        insert_dict['payment_vkey'] = key_created.get("payment_vkey")
        insert_dict['stake_addr'] = key_created.get("stake_addr")
        insert_dict['stake_skey'] = key_created.get("stake_skey")
        insert_dict['stake_vkey'] = key_created.get("stake_vkey")
        insert_dict['hash_verification_key'] = key_created.get("hash_verification_key")
        columns = list(insert_dict.keys())
        values = list(insert_dict.values())
        id = insert(tableName, columns, values)
        # query = f"SELECT name, base_addr, payment_addr, stake_addr FROM wallet WHERE id = '{id}'"
        # response = read_query(query)
    else:
        id = None
    payload = {
        "wallet_save_locally": key_save_flag,
        "id": id,
        "wallet_name": wallet_name,
        "mnemonic": key_created.get("mnemonic"),
        "root_key": key_created.get("root_key"),
        "private_stake_key": key_created.get("private_stake_key"),
        "private_payment_key": key_created.get("private_payment_key"),
        "payment_account_key": key_created.get("payment_account_key"),
        "stake_account_key": key_created.get("stake_account_key"),
        "payment_addr": key_created.get("payment_addr"),
        "base_addr": key_created.get("base_addr"),
        "hash_verification_key": key_created.get("hash_verification_key"),
    }
    return(payload)

def query_wallet(tableName: str, **kwargs) -> List:
    conditions = kwargs['conditions']
    condition = ''
    for k, v in conditions.items():
        condition += k + "='" + v + "' and " 
    condition = condition[:-5]

    query = f"SELECT * FROM {tableName} WHERE {condition};"
    return read_query(query)

def insert_transaction(tx_info: dict, config_path: str) -> Union[int, None]:
    tableName = 'transactions'
    insert_dict = {}
    insert_dict['id'] = tx_info['tx_id']
    insert_dict['id_wallet'] = tx_info['wallet_origin_id']
    insert_dict['address_origin'] = tx_info['tx_details']['address_origin']
    insert_dict['address_destin'] = str([address['address'] for address in tx_info['tx_details']['address_destin']])
    insert_dict['metadata'] = tx_info['tx_details']['metadata']
    insert_dict['network'] = base.Starter(config_path).CARDANO_NETWORK
    success_flag = tx_info['success_flag']
    insert_dict['processed'] = success_flag
    fees = tx_info.get('fees', None)
    if success_flag:
        cbor_tx_path = base.Starter(config_path).TRANSACTION_PATH_FILE + '/tx.signed'
        insert_dict['fees'] = fees
        with open(cbor_tx_path, 'r') as file:
            cbor_tx_file = json.load(file)
    elif fees is not None:
        cbor_tx_path = base.Starter(config_path).TRANSACTION_PATH_FILE + '/tx.draft'
        insert_dict['fees'] = fees
        with open(cbor_tx_path, 'r') as file:
            cbor_tx_file = json.load(file)
    else:
        cbor_tx_file = {"msg": tx_info['msg']}
    insert_dict['tx_cborhex'] = cbor_tx_file
    columns = list(insert_dict.keys())
    values = list(insert_dict.values())
    id = insert(tableName, columns, values)
    return id

def get_address_origin(tableName: str, id: str) -> Tuple[str, str]:
    tableName = 'wallet'
    conditions = { 'id': id}
    query_results = query_wallet(tableName, conditions=conditions)
    address_origin = query_results[0][3]
    payment_vkey = query_results[0][4]
    payment_vkey = json.dumps(payment_vkey)

    return (address_origin, payment_vkey)

def insert_script(script_name: str, purpose: str, multisig_script: dict, policyID: str) -> Union[int, None]:

    tableName = 'scripts'
    insert_dict = {}
    insert_dict['name'] = script_name
    insert_dict['purpose'] = purpose
    insert_dict['content'] = multisig_script
    insert_dict['policyid'] = policyID
    columns = list(insert_dict.keys())
    values = list(insert_dict.values())
    return insert(tableName, columns, values)

if __name__ == '__main__':
    config_path = './backend/config.ini'
    connect()
    create_tables()


# def write_query(command):
#     conn = None
#     id = 0
#     try:
#         # read the connection parameters
#         params = config(config_path, section='postgresql')
#         # connect to the PostgreSQL server
#         conn = psycopg2.connect(**params)
#         cur = conn.cursor()
#         # create table one by one
#         cur.execute(command)
#         result = cur.fetchone()
#         if result is not None:
#             id = result[0]
#         conn.commit()
#         print ('\nfinished CREATE OR INSERT TABLES execution')
#         cur.close()
#         return id
#     except (Exception, psycopg2.DatabaseError) as error:
#         print(error)
#         if conn is not None:
#             conn.rollback()
#         return None
#     finally:
#         if conn is not None:
#             conn.close()

# def build_column_values(columns, value_dict):
#     column_list = []
#     values = []
#     for column in columns:
#         # This is a way to take only the values needed to build the DB table
#         if column in value_dict:
#             if value_dict[column]:
#                 column_list.append(column)
#                 # If it is a string, the value should go with ''
#                 if type(value_dict[column]) == str:
#                     value = value_dict[column].replace("'", "''")
#                     value = "'" + value + "'"
#                 else:
#                     value = value_dict[column]
#                 values += [str(value)]
        
#     return column_list, values