from setuptools import setup

setup(
    name='okapi',
    version='0.0.1',
    description='The funniest joke in the world',
    url='http://github.com/storborg/funniest',
    author='Abirafdi Raditya Putra',
    author_email='raditya.putra@unit9.com',
    license='MIT',
    packages=['okapi'],
    install_requires=[
        'pytest',
        'requests==2.20.1',
        'requests-toolbelt==0.8.0',
    ],
    zip_safe=False
)
