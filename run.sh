#!/bin/bash

a="env/bin/activate"
python_file="env/bin/python"
filepath="${PWD}/${a}"
pythonpath="${PWD}/${python_file}"
echo "filepath: "${filepath}
files=$(dir)
echo "directory files: "${files}
source $filepath
./env/bin/python quickstart.py

