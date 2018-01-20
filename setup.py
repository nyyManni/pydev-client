
from setuptools import setup


setup(name='pydevc',
      description='Command-line interface to PyDev debugger',
      version='0.1',
      packages=[
          'pydevc'
      ],
      entry_points={
          'console_scripts': [
              'pydevc = pydevc.__main__:main'
          ]
      },
      install_requires=[

          # PyDev Daemon
          'pydevd==1.1.1'
      ])
