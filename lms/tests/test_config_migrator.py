import os
import shutil

from lms import lmsweb
from lms.tests import conftest


CONFIG_EXAMPLE_FILE = os.path.join(conftest.SAMPLES_DIR, 'config.py.example')
CONFIG_COPY_FILE = os.path.join(conftest.SAMPLES_DIR, 'config_copy.py')
CONFIG_FILE = os.path.join(conftest.SAMPLES_DIR, 'config.py')


class TestConfigMigrator:
    @staticmethod
    def setup():
        shutil.copyfile(CONFIG_COPY_FILE, CONFIG_FILE)

    @staticmethod
    def teardown():
        os.remove(CONFIG_FILE)

    @staticmethod
    def test_config_migration():
        missing_files = lmsweb.config_migrator(
            CONFIG_FILE, CONFIG_EXAMPLE_FILE,
        )
        config_values, _ = lmsweb.get_configs_values(
            CONFIG_FILE, CONFIG_EXAMPLE_FILE,
        )
        for file in missing_files:
            assert file in config_values
