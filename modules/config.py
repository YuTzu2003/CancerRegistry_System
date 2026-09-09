import os


def get_env(name):
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"環境變數 {name} 未設定")
    return value


def get_int_env(name):
    value = get_env(name)
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f"環境變數 {name} 必須是整數") from error
