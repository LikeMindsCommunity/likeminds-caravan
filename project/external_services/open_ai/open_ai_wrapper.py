import requests, os, base64

from openai import OpenAI

from utility.response_utilities import ResponseUtilities
from utility.states import attachment_types

from external_services.amazon_s3.s3_utils import S3_Utils
from external_services.logging.logging_wrapper import LoggingWrapper

from external_services.open_ai.constants import (DEFAULT_VISION_MODEL,
                                                 ERROR_INVALID_REQUEST_BODY_FOR_VALIDATING_OPENAI_API_KEY)

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class OpenAiWrapper:
    
    client = None
    
    api_key = ""
    vision_model = ""

    def __init__(self, api_key: str = "", vision_model: str = ""):
        self.api_key = api_key
        self.vision_model = vision_model
        
        self.client = OpenAI(api_key=self.api_key)

    def validate_open_ai_api_key_or_assistant(self, assistant_id: str = "") -> dict:

        if not self.api_key:
            return ResponseUtilities.get_inner_error_context(
                ERROR_INVALID_REQUEST_BODY_FOR_VALIDATING_OPENAI_API_KEY
            )

        try:

            if assistant_id:
                # Make a simple API call to retrieve assistant
                self.client.beta.assistants.retrieve(assistant_id)

            else:
                # Make a simple API call to list models (a lightweight operation)
                self.client.models.retrieve("gpt-3.5-turbo-instruct")

            return {"success": True}

        except Exception as e:
            error_logger.error(
                f"Exception occurred while setting up OpenAI's API Key | Error: {e.args}"
            )

            if e.body and isinstance(e.body, dict) and e.body.get("code"):
                error_message = e.body.get("code")
            elif e.body and isinstance(e.body, dict) and e.body.get("message"):
                error_message = e.body.get("message")
            else:
                error_message = e.args[0]

            return ResponseUtilities.get_inner_error_context(
                f"Error occured validating OpenAI's API Key: {error_message}"
            )

    def run_thread_and_fetch_latest_message_for_open_ai_assistant(
        self,
        assistant_id: str,
        message: str,
        attachments: list = [],
        thread_id: str = "",
        max_completion_tokens: int = 0,
        max_prompt_tokens: int = 0,
    ) -> dict:

        if not (assistant_id and self.api_key):
            return { "error_message": f"Invalid request parameters for OpenAI API call: {assistant_id}, {message}, {self.api_key}"}
            
        if not (message or attachments):
            return { "error_message": f"Invalid request parameters for OpenAI API call: {assistant_id}, {message}, {attachments}"}

        try:
            params, messages = self.prepare_params_for_run(
                message, attachments, assistant_id, max_completion_tokens, max_prompt_tokens
            )

            return self.create_run_and_fetch_latest_message_and_thread_id(params, messages, thread_id)

        except Exception as e:
            return { "error_message": f"Error while calling OpenAI API for assistant_id: {assistant_id} and api_key: {self.api_key}: {str(e)} " }
            
    def prepare_params_for_run(
        self,
        message:str,
        attachments: list = [],
        assistant_id: str = "", 
        max_completion_tokens: int = 0, 
        max_prompt_tokens: int = 0,
    ):
        
        image_attachment_present = False
        content = []
        
        if message:
            content.append({ "type": "text", "text": message})
            
        for attachment in attachments:
            
            if attachment.get("type") == attachment_types.IMAGE:
                image_attachment_present = True
                image_file_id = self.dowload_file_from_url_and_upload_to_open_ai(attachment.get("url"))
                if image_file_id:
                    content.append({ "type": "image_file", "image_file": { "file_id": image_file_id}})
                
            elif attachment.get("type") == attachment_types.AUDIO:
                transcribed_text = self.transcribe_audio(attachment.get("url"))
                if transcribed_text:
                    content.append({ "type": "text", "text": transcribed_text})
                else:
                    content.append({ "type": "text", "text": "Some error occurred while transcribing \
                                                                the audio, please reply appropriately"})
        
        messages = [ {"role": "user", "content": content} ]
        params = { "assistant_id": assistant_id}

        if max_completion_tokens:
            params["max_completion_tokens"] = max_completion_tokens

        if max_prompt_tokens:
            params["max_prompt_tokens"] = max_prompt_tokens
            
        if image_attachment_present:
            if self.vision_model:
                params["model"] = self.vision_model
            else:
                params["model"] = DEFAULT_VISION_MODEL
                
        return params, messages   
    
    def create_run_and_fetch_latest_message_and_thread_id(self, params: dict, messages: list, thread_id: str) -> dict:
        try:
            
            # If thread_id is present, call OpenAI API with thread_id else create a new thread
            if thread_id:
                run = self.client.beta.threads.runs.create_and_poll(
                    **params, thread_id=thread_id, additional_messages=messages
                )

            else:
                run = self.client.beta.threads.create_and_run_poll(
                    **params, thread={"messages": messages}
                )

            if run.thread_id:
                thread_id = run.thread_id

            # If run is completed, fetch latest message from thread
            if run.status == "completed":
                messages = self.client.beta.threads.messages.list(
                    thread_id=run.thread_id, limit=1
                )
                
            else:
                return {
                    "error_message": f"Error while creating thread for OpenAI API for assistant_id: {run.assistant_id} | status: {run.status} | incomplete details: {run.incomplete_details}",
                    "thread_id": thread_id
                }

            if len(messages.data) > 0 and len(messages.data[0].content) > 0:
                return {"response": messages.data[0].content[0].text.value, "thread_id": thread_id}
            else:
                return {
                    "error_message": f"Error while fetching latest message from OpenAI API for assistant_id: {run.assistant_id} | thread_id: {thread_id}",
                    "thread_id": thread_id
                }
                
        except Exception as e:
            return {
                "error_message": f"Exception occured while running and fetching latest message from OpenAI API for assistant_id: {run.assistant_id} | thread_id: {thread_id} | params: {params} | error: {str(e)}",
                "thread_id": thread_id
            }
            
    def transcribe_audio(self, audio_url: str = "") -> str:
        try:
            file_path = S3_Utils.download_file_from_s3_url(audio_url)
            if file_path:
                audio_file = open(file_path, "rb")
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )
                
                if transcription:
                    return transcription.text
                else:
                    return ""
            else:
                return ""
                    
        except Exception as e:
            error_logger.error(f"Error while transcribing audio for audio_url: {audio_url} | error: {str(e)}")
            return ""
        
        finally:
            if file_path:
                os.remove(file_path)
                
    def upload_file(self, file_path: str = "") -> str:
        try:
            file_obj = self.client.files.create(file=open(file_path, "rb"), purpose="vision")
            return file_obj.id
        except Exception as e:
            error_logger.error(f"Error while uploading file to open_ai | error: {str(e)}")
            return ""
                
    def dowload_file_from_url_and_upload_to_open_ai(self, file_url: str = "") -> str:
        try:
            file_path = S3_Utils.download_file_from_s3_url(file_url)
            if file_path:
                return self.upload_file(file_path)
            else:
                return ""
        except Exception as e:
            error_logger.error(f"Error while downloading file for file_url: {file_url} | error: {str(e)}")
            return ""
        finally:
            if file_path:
                os.remove(file_path)

