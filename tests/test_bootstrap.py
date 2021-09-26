from lms.lmsdb import bootstrap
from lms.lmsdb.models import User


class TestBootstrapper:
    @staticmethod
    def test_has_column_named_true_positive(db):
        assert bootstrap.has_column_named(db, User, 'username')

    @staticmethod
    def test_has_column_named_true_negative(db):
        assert not bootstrap.has_column_named(db, User, 'moshiko@')
