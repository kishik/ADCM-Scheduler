from neomodel import db, clear_neo4j_database
from django.test import TestCase


class YourTestClass(TestCase):
    def setUp(self):
        clear_neo4j_database(db)

    def test_something(self):
        pass
