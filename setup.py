from setuptools import setup


setup(
    name='cldfbench_borrowing-detection-study',
    py_modules=['cldfbench_bds'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'bds=lexibank_bds:Dataset',
        ],
        'cldfbench.commands': [
            'bds=bdscommands',
        ]
    },
    install_requires=[
        'cldfbench',
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
