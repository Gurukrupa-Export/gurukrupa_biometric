from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in gurukrupa_biometric/__init__.py
from gurukrupa_biometric import __version__ as version

setup(
	name="gurukrupa_biometric",
	version=version,
	description="Biometric",
	author="Gurukrupa Export",
	author_email="vihsal@gurukrupaexport.in",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
