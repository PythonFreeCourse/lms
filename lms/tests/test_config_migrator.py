import os
import pathlib
import shutil

from lms.utils import config_migrator
from lms.tests import conftest


CONFIG_EXAMPLE_FILE = pathlib.Path(conftest.SAMPLES_DIR) / 'config.py.example'
CONFIG_COPY_FILE = pathlib.Path(conftest.SAMPLES_DIR) / 'config_copy.py'
CONFIG_FILE = pathlib.Path(conftest.SAMPLES_DIR) / 'config.py'


class TestConfigMigrator:
    @staticmethod
    def setup():
        shutil.copyfile(str(CONFIG_COPY_FILE), str(CONFIG_FILE))

    @staticmethod
    def teardown():
        os.remove(str(CONFIG_FILE))

    @staticmethod
    def test_config_migration():
        missing_files = config_migrator.migrate(
            CONFIG_FILE, CONFIG_EXAMPLE_FILE,
        )
        config_values, _ = config_migrator.get_configs_values(
            CONFIG_FILE, CONFIG_EXAMPLE_FILE,
        )
        for file in missing_files:
            assert file in config_values
