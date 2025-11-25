from setuptools import setup, find_packages

setup(
    name="dubai-eta-prediction",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        line.strip() 
        for line in open('requirements.txt').readlines()
    ],
    author="Data Science Team",
    description="ETA Prediction System for Dubai Ride-Hailing Service",
    python_requires=">=3.8",
)