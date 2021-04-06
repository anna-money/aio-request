import re
from pathlib import Path

from setuptools import setup

install_requires = [
    "multidict>=4.5,<7.0",
    "yarl>=1.0,<2.0",
]


def read(*parts):
    return Path(__file__).resolve().parent.joinpath(*parts).read_text().strip()


def read_version():
    regexp = re.compile(r"^__version__\W*=\W*\"([\d.abrc]+)\"")
    for line in read("aio_request", "__init__.py").splitlines():
        match = regexp.match(line)
        if match is not None:
            return match.group(1)
    else:
        raise RuntimeError("Cannot find version in aio_request/__init__.py")


with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name="aio-request",
    version=read_version(),
    description="Various strategies for sending requests",
    long_description=long_description,
    long_description_content_type="text/markdown",
    platforms=["macOS", "POSIX", "Windows"],
    author="Yury Pliner",
    python_requires=">=3.8",
    project_urls={},
    author_email="yury.pliner@gmail.com",
    license="MIT",
    packages=["aio_request"],
    package_dir={"aio_request": "./aio_request"},
    package_data={"aio_request": ["py.typed"]},
    install_requires=install_requires,
    include_package_data=True,
)
