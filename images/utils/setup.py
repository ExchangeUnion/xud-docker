from setuptools import setup, find_packages

setup(
    name="launcher",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["toml", "docker", "demjson", "dockerpty"],
    include_package_data=True,
    package_data={
        "launcher.config": ["*.conf", "nodes.json"],
        "launcher": ["banner.txt"],
    }
)
