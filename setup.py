from setuptools import setup

setup(
    name="ObservationObject",
    version="0.1.0",
    description="Python class that simplifies working with telescope data",
    author="Fabian Gunnink",
    author_email="f.j.gunnink@student.rug.nl",
    url="https://github.com/PracticalAstronomyCrew/ObservationObject",
    packages=["ObservationObject"],
    install_requires=["astropy"],
)