from collabmates_api.multimedia_operations.constants import S3_CONSTANTS
from collabmates_api.multimedia_operations.mm_operations_manager import MultimediaOperationsManager
from external_services.amazon_s3.s3_client_impl import S3ClientImpl


class MultimediaOperationsImpl(MultimediaOperationsManager):

    s3_bucket = None

    def __init__(self, s3_bucket: dict):
        self.s3_bucket = s3_bucket

    def get_s3_bucket(self) -> dict:
        return self.s3_bucket

    def set_s3_bucket(self, s3_bucket: dict) -> None:
        self.s3_bucket = s3_bucket

    def generate_presigned_post(self, object_path: str) -> dict:
        s3_client = S3ClientImpl(self.get_s3_bucket())
        return s3_client.generate_presigned_post(object_path,
                                                 S3_CONSTANTS.get('PRE_SIGNED_URI_EXPIRATION_DELAY'))
