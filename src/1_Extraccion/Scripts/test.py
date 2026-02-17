from utils.paths import data_dir_path

filepath = data_dir_path() / "appid_list.json.gz"
print(filepath.name)