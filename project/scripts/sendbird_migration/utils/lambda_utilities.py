import requests


class LambdaUtilities:

    lambda_prod_url = "LAMBDA_URL"
    lambda_beta_url = "LAMBDA_URL"

    @staticmethod
    def migrate_to_s3(file_url, file_path, is_prod) -> str :

        payload = {
            "file_url": file_url,
            "file_path": file_path,
            "is_prod": is_prod
        }

        lambda_url = LambdaUtilities.lambda_prod_url if is_prod else LambdaUtilities.lambda_beta_url

        response = requests.post(lambda_url, json=payload)
        if response.status_code != 200:
            print(f"Error: {response.json()}")
            return ""

        public_url = response.json().get("s3_url")

        return public_url
