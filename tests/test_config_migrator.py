import os
import pathlib
import shutil

from lms.utils import config_migrator
from tests import conftest


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
        config_migrator.migrate(CONFIG_FILE, CONFIG_EXAMPLE_FILE)
        get_assignments = config_migrator.get_config_assignments
        new = get_assignments(CONFIG_FILE).keys()
        old = get_assignments(CONFIG_EXAMPLE_FILE).keys()
        assert len(old - new) == 0
