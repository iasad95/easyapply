import os


ELEMENT_WAIT_TIMEOUT = 15


class EnvironmentKeys:

    def __init__(self):
        self.skip_apply: bool = self._read_env_key_bool("SKIP_APPLY")
        self.disable_description_filter: bool = self._read_env_key_bool("DISABLE_DESCRIPTION_FILTER")

    @staticmethod
    def _read_env_key_bool(key: str) -> bool:
        value = os.getenv(key)
        if value is None:
            return False
        return value == "True"

    def print_config(self):
        print("\nEnv config:")
        print(f"\t- SKIP_APPLY: {self.skip_apply}\n")
        print(f"\t- DISABLE_DESCRIPTION_FILTER: {self.disable_description_filter}\n")
        print("\n")
