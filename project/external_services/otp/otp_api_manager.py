import abc


class OTPApiManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'send_otp_via_gupshup') and callable(subclass.send_otp_via_gupshup)) and
                (hasattr(subclass, 'send_retry_otp_via_msg_91') and callable(subclass.send_retry_otp_via_msg_91)) and
                (hasattr(subclass, 'verify_otp_via_gupshup') and callable(subclass.verify_otp_via_gupshup)) and
                (hasattr(subclass, 'verify_retry_otp_via_msg_91') and callable(subclass.verify_retry_otp_via_msg_91))
                or NotImplemented)

    @staticmethod
    def send_otp_via_gupshup(phone_number, international) -> dict:
        """
        Sends OTP on a phone number using gupshup vendor
        @param phone_number:
        @param international:
        """
        raise NotImplementedError

    @staticmethod
    def send_retry_otp_via_msg_91(phone_number) -> dict:
        """
        Sends OTP on a phone number using msg 91 vendor
        @param phone_number:
        """
        raise NotImplementedError

    @staticmethod
    def verify_otp_via_gupshup(phone_number, otp, is_international) -> dict:
        """
        Verifies OTP using gupshup API
        @param phone_number:
        @param otp:
        @param is_international:
        """
        raise NotImplementedError

    @staticmethod
    def verify_retry_otp_via_msg_91(phone_number, otp) -> dict:
        """
        Verifies OTP using msg 91 API
        @param phone_number:
        @param otp:
        """
        raise NotImplementedError
