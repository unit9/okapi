from setuptools import setup

setup(
    name='okapi',
    version='0.0.1',
    description='Set of tools to help wraps REST-like web APIs',
    url='http://github.com/unit9/okapi',
    author='Abirafdi Raditya Putra',
    author_email='raditya.putra@unit9.com',
    license='MIT',
    packages=['okapi'],
    install_requires=[
        'requests==2.*',
        'requests-toolbelt>=0.9.1',
    ],
    zip_safe=False
)
