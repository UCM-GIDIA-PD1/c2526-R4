from pathlib import Path

def proyect_root():
    return Path(__file__).resolve().parents[4]

def data_path():
    return proyect_root() / "data"

def config_path():
    return proyect_root() / "config"

def error_log_path():
    return data_path() / "error_logs"

if __name__ == "__main__":
    print(proyect_root())