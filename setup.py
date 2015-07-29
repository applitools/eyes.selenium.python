from distutils.core import setup
from applitools import VERSION

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
    long_description="""\
    Applitools Eyes SDK For Selenium Python WebDriver.

    Sample scripts are available inside the distribution under the 'samples' directory.
    """,
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
    install_requires=[
        'setuptools',
        'requests>=2.1.0',
        'pypng>=0.0.16',
        'selenium>=2.43.0',
        'Appium-Python-Client>=0.13'
    ]
)
