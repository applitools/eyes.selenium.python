import codecs
import os
import re
import sys

from os import path
from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))


def read(filename):
    return codecs.open(path.join(here, filename), 'r', 'utf-8').read()


# preventing ModuleNotFoundError caused by importing lib before installing deps
def get_version():
    with open(os.path.join(os.path.abspath('.'), 'applitools/__version__.py'), 'r') as f:
        try:
            version = re.findall(r"^__version__ = '([^']+)'\r?$",
                                 f.read(), re.M)[0]
        except IndexError:
            raise RuntimeError('Unable to determine version.')
    return version


install_requires = [
    "requests>=2.1.0,<2.21.0",
    "selenium>=2.53.0,<4",
    "Pillow>=5.0.0,<7.0.0",
    "tinycss2==0.6.1",
]
# using this way of defining instead of 'typing>=3.5.2; python_version<="3.4"'
# for run on old version of setuptools without issues
if sys.version_info < (3, 5):
    # typing module was added as builtin in Python 3.5
    install_requires.append('typing >= 3.5.2')

setup(
    name='eyes-selenium',
    version=get_version(),
    packages=find_packages(exclude=('tests',)),
    url='http://www.applitools.com',
    license='Apache License, Version 2.0',
    author='Applitools Team',
    author_email='team@applitools.com',
    description='Applitools Eyes SDK For Selenium Python WebDriver',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing"
    ],
    keywords='applitools eyes selenium',
    install_requires=install_requires,
    extras_require={
        'dev':     [
            'bumpversion',
            'flake8',
            'flake8-import-order',
            'flake8-bugbear',
            'mypy',
            'towncrier',
        ],
        'testing': [
            'pytest < 4.0.0',
            'pytest-cov',
            'pytest-xdist',
            'mock'
        ],
    },
    package_data={
        '':           ['README.md', 'samples'],
        'applitools': ['py.typed'],
    },
    project_urls={
        'Bug Reports':                  'https://github.com/applitools/eyes.selenium.python/issues',
        'Selenium Python example':      'https://applitools.com/resources/tutorial/selenium/python#step-2',
        'Python Appium native example': 'https://applitools.com/resources/tutorial/appium/native_python#step-2',
        'Python Appium web example':    'https://applitools.com/resources/tutorial/appium/python#step-2',
        'Source':                       'https://github.com/applitools/eyes.selenium.python',
    },
)
