# flake8: noqa


class TestStudent:
    """python"""
    def test_check_foo_foo(self):
        """שם כזה מגניב"""
        assert foo() == 'foo'

    def test_check_bar_bar(self):
        """שם כזה מגניב 2"""
        assert foo('bar') == 'barbaron', 'איזה ברברון'

    def test_check_foo_bar_foo(self):
        """שם כזה מגניב 3"""
        assert foo() == 'foofoon'
