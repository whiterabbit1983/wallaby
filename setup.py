from setuptools import setup, find_packages


setup(
    name="wallaby",
    version="0.1.0",
    description="A simple, functional wrapper around the wallaroo API",
    author="KEA",
    packages=find_packages(
        exclude=[
            "*test*",
            "*build*",
            "*__pycache__*",
            "*wallaroo*"
        ],
        include=['wallaby.py']
    ),
    license="LICENSE",
    long_description=open("README.md").read(),
    data_files=[(".", ["README.md", "LICENSE"])],
)
