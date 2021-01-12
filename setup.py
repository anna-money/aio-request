import os
import re

from setuptools import setup, find_packages

install_requires = [
    'aiohttp>=3.7.0',
    "multidict>=4.5,<7.0",
    "yarl>=1.0,<2.0",
]


def read_version():
    regexp = re.compile(r"^__version__\W*=\W*'([\d.abrc]+)'")
    init_py = os.path.join(os.path.dirname(__file__), 'aio_request', '__init__.py')
    with open(init_py) as f:
        for line in f:
            match = regexp.match(line)
            if match is not None:
                return match.group(1)
        else:
            raise RuntimeError('Cannot find version in aio_request/__init__.py')


setup(
    name='aio-request',
    version=read_version(),
    description='Various strategies for sending requests',
    platforms=['macOS', 'POSIX', 'Windows'],
    author='Yury Pliner',
    python_requires='>=3.8',
    project_urls={
    },
    author_email='yury.pliner@gmail.com',
    license='MIT',
    packages=find_packages(),
    install_requires=install_requires,
    include_package_data=True
)
