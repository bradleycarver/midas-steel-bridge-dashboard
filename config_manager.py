import os
import sys
import configparser

def get_base_dir():
    """Returns the directory where the EXE or the script is located."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(get_base_dir(), "config.ini")

def get_api_key():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
        try:
            return config.get('SETTINGS', 'api_key')
        except:
            return "my_api_key"
    else:
        config['SETTINGS'] = {'api_key': 'PASTE_KEY_HERE'}
        with open(CONFIG_PATH, 'w') as f:
            config.write(f)
        return "my_api_key"