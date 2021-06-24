from setuptools import setup


setup(
    name='lexibank_seabor',
    py_modules=['lexibank_seabor'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'lexibank.dataset': [
            'seabor=lexibank_seabor:Dataset',
        ],
        'cldfbench.commands': [
            'seabor=seaborcommands',
        ]
    },
    install_requires=[
        'pylexibank',
        'lingrex',
        'collabutils',
        'cartopy',
        'python-igraph',
        'scipy',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
