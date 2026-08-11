from neo4j import GraphDatabase
from django.conf import settings

class Neo4jConnection:
    _driver = None

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(
                settings.COGNODB_URI,
                auth=(settings.COGNODB_USER, settings.COGNODB_PASSWORD)
            )
        return cls._driver

    @classmethod
    def close_driver(cls):
        if cls._driver is not None:
            cls._driver.close()
            cls._driver = None

    @classmethod
    def execute_query(cls, query, **parameters):
        driver = cls.get_driver()
        return driver.execute_query(query, **parameters)


def execute_query(query, **parameters):
    """
    Centralized query execution helper for Neo4j graph queries.
    """
    return Neo4jConnection.execute_query(query, **parameters)
