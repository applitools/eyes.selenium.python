import sys

from codecs import open
from os import path

from setuptools import setup
from applitools import VERSION


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

install_requires = [
    'requests>=2.1.0',
    'pypng>=0.0.16',
    'selenium>=2.43.0',
    'Appium-Python-Client>=0.13'
]

if sys.version_info < (3, 5):
    install_requires.append('typing >= 3.5.2')
    install_requires.append('enum34 >= 1.1.6')

setup(
    name='eyes-selenium',
    version=VERSION,
    packages=['applitools', 'applitools.utils'],
    data_files=[('samples', ['samples/test_script.py'])],
    url='http://www.applitools.com',
    license='Apache License, Version 2.0',
    author='Applitools Team',
    author_email='team@applitools.com',
    description='Applitools Eyes SDK For Selenium Python WebDriver',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing"
    ],
    keywords='applitools eyes selenium',
    install_requires=install_requires,
    extras_require={
        'dev': ['ipython', 'ipdb', 'pylama', 'bumpversion', 'mypy'],
        'test': ['pytest'],
    },
    package_data={
        'applitools': ['py.typed'],
    },
    project_urls={
        'Bug Reports': 'https://github.com/applitools/eyes.selenium.python/issues',
        'Selenium Python example': 'https://applitools.com/resources/tutorial/selenium/python#step-2',
        'Python Appium native example': 'https://applitools.com/resources/tutorial/appium/native_python#step-2',
        'Python Appium web example': 'https://applitools.com/resources/tutorial/appium/python#step-2',
        'Source': 'https://github.com/applitools/eyes.selenium.python',
    },
)
