from setuptools import setup, find_packages

setup(
    name="leo_chat",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'beautifulsoup4',
        'streamlit',
        'sentence-transformers',
        'faiss-cpu',
        'motor',
        'pymongo[srv]',
        'pydantic'
    ],
) 