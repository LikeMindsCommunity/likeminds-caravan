#MSG91 API urls
MSG91_SENDOTP_URI = 'https://api.msg91.com/api/v5/otp?authkey=%s&extra_param={"COMPANY_NAME":"LikeMinds"}&template_id=%s&mobile=%s&invisible=0&otp_expiry=10'
MSG91_VERIFYOTP_URI = 'https://api.msg91.com/api/v5/otp/verify?authkey=%s&mobile=%s&otp=%s'

#SMS Gupshup api
SMSGUPSHUP_SMS_URI = 'http://enterprise.smsgupshup.com/GatewayAPI/rest?method=SendMessage&send_to={0}&msg={1}&msg_type=TEXT&userid={2}&auth_scheme=plain&password={3}&v=1.1&format=text'
