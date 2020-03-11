from setuptools import setup, find_packages

setup(
    name="launcher",
    version="1.0.0",
    packages=find_packages(),
    scripts=["bin/args_parser", "bin/config_parser"],
    install_requires=["toml", "docker", "demjson"],
    include_package_data=True,
    package_data={
        "launcher.config": ["*.conf", "nodes.json"],
        "launcher.shell": ["banner.txt"],
    }
)
