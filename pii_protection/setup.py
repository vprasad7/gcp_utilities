from setuptools import setup, find_packages
setup(
    name='ingestion-dataflow-setup',
    version='1.0',
    install_requires=[
        'google-cloud-storage == 1.32.0',
        'google-api-python-client == 2.0.2',
        'ndjson'
    ],
    description='Setup for Ingestion Dataflow',
    packages = find_packages(),
)