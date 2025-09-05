from setuptools import setup, find_packages

setup(
    name="file-organizer",
    version="1.0.0",
    description="Cross-platform File Organizer App with PyQt5 GUI (v1 & v2)",
    author="Harsh Kesharwani",
    author_email="harsh.kesharwani037@gmail.com",
    url="https://github.com/Harsh-GitHup/file-organizer",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "file_organizer": ["icons/*.png", "organizer_config.json"],
    },
    python_requires=">=3.9",
    install_requires=[
        "PyQt5>=5.15",
        "watchdog>=3.0.0",
        "appdirs>=1.4.4",
    ],
    entry_points={
        "console_scripts": [
            "file-organizer-v1=file_organizer.v1.main:main",
            "file-organizer-v2=file_organizer.v2.main:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
