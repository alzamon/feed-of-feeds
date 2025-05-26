class ConfigManager:
    """A trivial configuration manager that only holds the config path."""

    def __init__(self, config_path: str):
        self.config_path = config_path
