from configparser import ConfigParser
import hashlib
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")

def load_hash_keys(config_path=CONFIG_PATH):
    config = ConfigParser()
    config.read(config_path)
    keys_str = config.get("HASH", "keys")
    keys = [k.strip() for k in keys_str.split(",")]
    return keys


def generate_hash(data: dict, keys: list):
    """
    data: dictionary containing transaction fields
    keys: list of field names to include in hash
    """
    combined = ""

    for key in keys:
        value = str(data.get(key, "")).lower().strip()
        combined += value + "|"

    return hashlib.sha256(combined.encode()).hexdigest()[:32]

def add_hash(mails):
    keys = load_hash_keys()
    for mail in mails:
        mail['hashcode'] = generate_hash(mail, keys)
    return mails
