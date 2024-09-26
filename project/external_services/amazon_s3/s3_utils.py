import requests

from utility.utils import get_file_name_from_url
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

class S3_Utils():
        
    @staticmethod
    def download_file_from_s3_url(url: str) -> str:
        
        file_name = get_file_name_from_url(url)
        download_file_path = f"/tmp/{file_name}"

        try:
            response = requests.get(url)
            with open(download_file_path, "wb") as file:
                file.write(response.content)
                
            return download_file_path
        except Exception as e:
            error_logger.error(f"Error while downloading file from s3 url: {url} | Error: {str(e)}")
            return "" 
