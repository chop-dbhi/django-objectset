from setuptools import setup, find_packages

kwargs = {
    # Packages
    'packages': find_packages(exclude=['tests', '*.tests', '*.tests.*', 'tests.*']),
    'include_package_data': True,

    # Dependencies
    'install_requires': ['django'],

    'test_suite': 'test_suite',

    # Metadata
    'name': 'django-objectset',
    'version': __import__('objectset').get_version(),
    'author': 'Byron Ruth',
    'author_email': 'b@devel.io',
    'description': 'ObjectSet abstract class for set-like models',
    'license': 'BSD',
    'keywords': 'object set',
    'url': 'http://cbmi.github.com/django-objectset/',
    'classifiers': [
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Framework :: Django',
        'Topic :: Internet :: WWW/HTTP',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Information Technology',
    ],
}

setup(**kwargs)
