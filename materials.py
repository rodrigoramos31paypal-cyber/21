"""PDFs privados: autorização é feita antes de invocar este módulo."""
import os
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from flask import jsonify, redirect, send_from_directory

def deliver_material(root, name, production):
    bucket = os.environ.get('FOCO_MATERIALS_BUCKET')
    if bucket:
        try:
            client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-west-1'),
                                  config=Config(signature_version='s3v4'))
            prefix = os.environ.get('FOCO_MATERIALS_PREFIX', 'foco').strip('/')
            key = '/'.join(filter(None, [prefix, name]))
            url = client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key,
                'ResponseContentType': 'application/pdf', 'ResponseCacheControl': 'private, no-store'}, ExpiresIn=60)
            response = redirect(url, 302)
        except (BotoCoreError, ClientError):
            return jsonify(error='Não foi possível abrir o material.'), 503
    elif not production:
        response = send_from_directory(root / 'private_materials', name)
    else:
        return jsonify(error='A biblioteca privada ainda não está configurada.'), 503
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response
