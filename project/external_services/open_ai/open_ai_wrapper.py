import requests, os, base64

from openai import OpenAI

from utility.response_utilities import ResponseUtilities
from utility.states import attachment_types

from external_services.amazon_s3.s3_utils import S3_Utils
from external_services.logging.logging_wrapper import LoggingWrapper

from external_services.open_ai.constants import DEFAULT_VISION_MODEL

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
                "Invalid request body for validating openAi api key"
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
            return {
                "error_message": f"Invalid request parameters for OpenAI API call: {assistant_id}, {message}, {self.api_key}"
            }
            
        if not (message or attachments):
            return {
                "error_message": f"Invalid request parameters for OpenAI API call: {assistant_id}, {message}, {attachments}"
            }

        try:
            image_attachment_present = False
            content = [ { "type": "text", "text": message } ]
            
            for attachment in attachments:
                
                if attachment.get("type") == attachment_types.IMAGE:
                    image_attachment_present = True
                    base64_image = self.get_base64_encoded_image_from_url(attachment.get("url"))
                    content.append({ 
                                    "type": "image_url", 
                                    "image_url": { "url": f"data:image/jpeg;base64,{base64_image}"}
                                    }
                                )
                    
                elif attachment.get("type") == attachment_types.AUDIO:
                    transcribed_text = self.transcribe_audio(attachment.get("url"))
                    if transcribed_text:
                        content.append({ "type": "text", "text": transcribed_text})
                    else: #TODO: Confirm the output of this
                        content.append({ "type": "text", "text": "Some error occurred while transcribing the audio"})
            
            messages = [
                {"role": "user", "content": content},
            ]
            
            params = {
                "assistant_id": assistant_id,
            }

            if max_completion_tokens:
                params["max_completion_tokens"] = max_completion_tokens

            if max_prompt_tokens:
                params["max_prompt_tokens"] = max_prompt_tokens
                
            if image_attachment_present:
                if self.vision_model:
                    params["model"] = self.vision_model
                else:
                    params["model"] = DEFAULT_VISION_MODEL

            # If thread_id is present, call OpenAI API with thread_id else create a new thread
            thread_id = ""
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
                    "error_message": f"Error while creating thread for OpenAI API for assistant_id: {assistant_id} | status: {run.status} | incomplete details: {run.incomplete_details}"
                }

            if len(messages.data) > 0 and len(messages.data[0].content) > 0:
                response = messages.data[0].content[0].text.value
            else:
                return {
                    "error_message": f"Error while fetching latest message from OpenAI API for assistant_id: {assistant_id} | thread_id: {thread_id}"
                }

            return {"response": response, "thread_id": thread_id}

        except Exception as e:
            return {
                "error_message": f"Error while calling OpenAI API for assistant_id: {assistant_id} and api_key: {self.api_key}: {str(e)} "
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
                
    def get_base64_encoded_image_from_url(self, image_url: str = "") -> str:
        
        # file_obj = self.client.files.create(file=open("test.jpg", "rb")) ##Use file_obj.id in message content
        
        try:
            file_path = S3_Utils.download_file_from_s3_url(image_url)
            if file_path:
                return self.encode_image(file_path)
            else:
                return ""
            
        except Exception as e:
            error_logger.error(f"Error while downloading image for image_url: {image_url} | error: {str(e)}")
            return ""
        
        finally:
            if file_path:
                os.remove(file_path)
        
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
                