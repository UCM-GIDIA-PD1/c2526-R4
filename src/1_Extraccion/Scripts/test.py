from utils.config import data_path

filepath = data_path() / "appid_list.v1.json.gz"
print(filepath.suffixes == [""])