
from setuptools import setup


setup(
    name='pydevc',
    description='Command-line interface to PyDev debugger',
    author='Henrik Nyman',
    author_email='henrikjohannesnyman@gmail.com',
    url='http://github.com/nyyManni/pydev-client',
    license='GPLv3',
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
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Debuggers',
    ]
)
