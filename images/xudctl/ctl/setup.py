import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="ctl",
    version="0.1.0",
    scripts=[],
    author="Yang Yang",
    author_email="reliveyy@gmail.com",
    description="A wrapper program for xud-docker",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=setuptools.find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    entry_points={
        "console_scripts": [
            "ctl = ctl.__main__:main",
            # This will not work because of the dash(-) between the package name
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "web3==4.9.2",
        "python-bitcoinrpc==1.0",
        "grpcio==1.20.1",
        "googleapis-common-protos==1.6.0",
    ],

)
