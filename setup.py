from setuptools import setup


setup(
    name             = "zdgrab",
    version          = "4.1.0",
    author           = "Brent Woodruff",
    author_email     = "brent@fprimex.com",
    url              = "http://github.com/fprimex/zdgrab",
    description      = "Get attachments from Zendesk tickets.",
    long_description = "Get attachments from Zendesk tickets.",
    keywords         = "zendesk attachment",
    license          = "Apache",
    zip_safe         = False,
    py_modules       = [
                         "zdgrab"
                       ],
    classifiers      = [
                         "Development Status :: 5 - Production/Stable",
                         "Intended Audience :: End Users/Desktop",
                         "License :: OSI Approved :: Apache Software License",
                         "Topic :: Utilities",
                       ],
    install_requires = [
                         "zdesk",
                         "zdeskcfg",
                         "asplode"
                       ],
    entry_points     = {
                         'console_scripts': [
                           'zdgrab  =  zdgrab:main',
                         ],
                       },
)
