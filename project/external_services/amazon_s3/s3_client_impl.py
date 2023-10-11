import logging

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

from external_services.amazon_s3.constants import PUBLIC_READ_ACL
from external_services.amazon_s3.s3_client_manager import S3ClientManager


class S3ClientImpl(S3ClientManager):

    s3_bucket = None
    logger = logging.getLogger("info_logger")

    def __init__(self, s3_bucket: dict):
        self.s3_bucket = s3_bucket

    def get_s3_bucket(self) -> dict:
        return self.s3_bucket

    def set_s3_bucket(self, s3_bucket: dict) -> None:
        self.s3_bucket = s3_bucket

    def generate_presigned_post(self, object_path: str, expiration: int) -> dict:

        fields = dict()
        self._add_public_read_acl_fields(fields)

        conditions = list()
        self._add_public_read_acl_condition(conditions)

        return self._generate_presigned_post_internal(self.get_s3_bucket().get('name'),
                                                      object_path,
                                                      fields,
                                                      conditions,
                                                      expiration)
    
    def upload_file_to_s3_bucket(self, object_path: str, file_path: str) -> bool:
        """
        Upload a file to an S3 bucket with public read access
        :param object_path: string
        :param file_path: string
        :return: True if file was uploaded, else False
        """

        bucket_name = self.get_s3_bucket().get('name')
        region_name = self.get_s3_bucket().get('region')

        s3_client = boto3.client('s3', region_name=region_name,
                                 aws_access_key_id=settings.AWS_CREDENTIALS.get('ACCESS_KEY'),
                                 aws_secret_access_key=settings.AWS_CREDENTIALS.get('SECRET_KEY'))
        
        try:
            s3_client.upload_file(object_path, bucket_name, file_path, ExtraArgs={'ACL': 'public-read'})
        except ClientError as e:
            self.logger.error(str(e))
            return False

        return True
    
    def fetch_files_from_s3_bucket(self, file_path: str):
        """
        fetch files from an S3 bucket on the basis of file path with public read access
        :param file_path: string
        """

        bucket_name = self.get_s3_bucket().get('name')
        region_name = self.get_s3_bucket().get('region')

        s3_client = boto3.client('s3', region_name=region_name,
                                 aws_access_key_id=settings.AWS_CREDENTIALS.get('ACCESS_KEY'),
                                 aws_secret_access_key=settings.AWS_CREDENTIALS.get('SECRET_KEY'))
        
        objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=file_path)

        return objects
        

    def _generate_presigned_post_internal(self,
                                          bucket_name: str,
                                          object_path: str,
                                          fields=None,
                                          conditions=None,
                                          expiration=3600) -> dict:
        """
        Generate a presigned URL S3 POST request to upload a file
        :param bucket_name: string
        :param object_path: string
        :param fields: Dictionary of prefilled form fields
        :param conditions: List of conditions to include in the policy
        :param expiration: Time in seconds for the presigned URL to remain valid
        :return: Dictionary with the following keys:
            url: URL to post to
            fields: Dictionary of form fields and values to submit with the POST
        :return: None if error.
        """

        s3_client = boto3.client('s3',
                                 region_name=self.get_s3_bucket().get('region'),
                                 aws_access_key_id=settings.AWS_CREDENTIALS.get('ACCESS_KEY'),
                                 aws_secret_access_key=settings.AWS_CREDENTIALS.get('SECRET_KEY'))
        try:
            response = s3_client.generate_presigned_post(bucket_name,
                                                         object_path,
                                                         Fields=fields,
                                                         Conditions=conditions,
                                                         ExpiresIn=expiration)
        except ClientError as e:
            self.logger.error(str(e))
            return dict()

        return response

    @staticmethod
    def _add_public_read_acl_fields(fields: dict) -> None:
        fields.update(PUBLIC_READ_ACL)

    @staticmethod
    def _add_public_read_acl_condition(conditions: list) -> None:
        conditions.append(PUBLIC_READ_ACL)
