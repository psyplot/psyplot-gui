"""Dummy module

Just a dummy module for documentation testing purposes"""


class DummyClass(object):
    """I am a test class for docs"""

    #: A dummy class attribute that will be replaced by an instance attribute
    a = None

    def __init__(self, a=None):
        """
        Parameters
        ----------
        a: object
            anything"""
        self.a = a

    def __call__(self, a=None):
        """
        Parameters
        ----------
        a: object
            anything else"""
        self.a = a

    def dummy_method(self, a=None):
        """A dummy instance method

        Parameters
        ----------
        a: object
            any dummy value"""
        self.a = a


def dummy_func(a=None):
    """A dummy test function

    Parameters
    ----------
    a: object
        I don't care"""
    pass


#: :class:`int`. A dummy module level attribute
a = 1
