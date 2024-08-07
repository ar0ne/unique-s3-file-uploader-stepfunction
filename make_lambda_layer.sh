#!/bin/bash

mkdir -p python
pip install PyMySQL==1.1.1 -t python/
zip -r pymysql.zip python
aws lambda publish-layer-version --layer-name pymysql-layer \
    --zip-file fileb://pymysql.zip \
    --compatible-runtimes python3.12 \
    --compatible-architectures "x86_64"

rm -rf python/
rm pymysql.zip
