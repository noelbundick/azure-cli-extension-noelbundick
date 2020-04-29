#!/usr/bin/env python

from setuptools import setup, find_packages

VERSION = "0.0.18"

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "License :: OSI Approved :: MIT License",
]

DEPENDENCIES = []

setup(
    name="noelbundick",
    version=VERSION,
    description="An Azure CLI extension that @acanthamoeba likes.",
    long_description="An Azure CLI extension that includes useful functionality that @acanthamoeba likes, but doesn't have time to write tests for.",
    license="MIT",
    author="Noel Bundick",
    author_email="noelbundick@gmail.com",
    url="https://github.com/noelbundick/azure-cli-extension-noelbundick",
    classifiers=CLASSIFIERS,
    packages=find_packages(),
    install_requires=DEPENDENCIES,
    package_data={
        "azext_noelbundick": [
            "azext_metadata.json",
            "self_destruct_template_sp.json",
            "self_destruct_template_mi.json",
        ]
    },
)
