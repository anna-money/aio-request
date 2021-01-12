import re
from pathlib import Path

from setuptools import setup, find_packages

install_requires = [
    "aiohttp>=3.7.0",
    "multidict>=4.5,<7.0",
    "yarl>=1.0,<2.0",
]


def read(*parts):
    return Path(__file__).resolve().parent.joinpath(*parts).read_text().strip()


def read_version():
    regexp = re.compile(r"^__version__\W*=\W*\"([\d.abrc]+)\"")
    for line in read("aio_request", "__init__.py").splitlines():
        print(line)
        match = regexp.match(line)
        if match is not None:
            return match.group(1)
    else:
        raise RuntimeError("Cannot find version in aio_request/__init__.py")


setup(
    name="aio-request",
    version=read_version(),
    description="Various strategies for sending requests",
    platforms=["macOS", "POSIX", "Windows"],
    author="Yury Pliner",
    python_requires=">=3.8",
    project_urls={},
    author_email="yury.pliner@gmail.com",
    license="MIT",
    packages=find_packages(),
    install_requires=install_requires,
    include_package_data=True,
)
