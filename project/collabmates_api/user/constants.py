from django.conf import settings
web_url = settings.WEB_URL

REMOVED_PROFILE_NAME = "Anonymous"
REMOVED_PROFILE_URL = "https://firebasestorage.googleapis.com/v0/b/collabmates-3d601.appspot.com/o/files%2Fmain_website%2Fuser.png?alt=media&token=8fd0a21e-6d77-4947-afc7-4d67eaf63b99"
VERIFICATION_EMAIL_EXPIRE_TIME = 86400      # 24 hours

LINKED_IN_WEB_ACCESS_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKED_IN_WEB_USER_URL = 'https://api.linkedin.com/v2/me?projection=(id,firstName,emailAddress,lastName,vanityName,headline,interests,location,picture-url,name,profilePicture(displayImage~:playableStreams))&oauth2_access_token='
LINKED_IN_WEB_EMAIL_URL = 'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))&oauth2_access_token='

GOOGLE_REGEX = "/AAAAAAAAAAI/AAAAAAAAAAA/"

HEADER_ACCESS_NOT_PART_OF_COMMUNITIES = 'This app is accessible to <<invited members|route://highlight>> only'
HEADER_ACCESS_ONE_PENDING_COMMUNITY = 'Pending approval'
HEADER_ACCESS_ONE_EXPIRED_COMMUNITY = 'Membership expired'

ACCESS_LOCK_ICON = 'https://prod-likeminds-media.s3.amazonaws.com/files/utilities/access_blocker_lock_icon.jpg'
ACCESS_MAIL_ICON = 'https://prod-likeminds-media.s3.amazonaws.com/files/utilities/access_blocker_mail_icon.jpg'
ACCESS_HEADER_IMAGE = 'https://prod-likeminds-media.s3.amazonaws.com/files/utilities/lottie_pending_request.json'

TITLE_ACCESS_NOT_PART_OF_COMMUNITIES = 'Have you received an invitation link?'
TITLE_ACCESS_ONE_PENDING_COMMUNITY = 'You are on the waiting list!'
TITLE_ACCESS_ONE_EXPIRED_COMMUNITY = 'Renew membership!'
TITLE_ACCESS_MORE_PENDING_COMMUNITIES = TITLE_ACCESS_ONE_PENDING_COMMUNITY
TITLE_ACCESS_MORE_EXPIRED_COMMUNITIES = 'Renew memberships!'
TITLE_ACCESS_MORE_PENDING_ONE_EXPIRED_COMMUNITIES = TITLE_ACCESS_ONE_EXPIRED_COMMUNITY
TITLE_ACCESS_MORE_PENDING_MORE_EXPIRED_COMMUNITIES = TITLE_ACCESS_MORE_EXPIRED_COMMUNITIES

SECOND_TITLE_ACCESS_NOT_PART_OF_COMMUNITIES = 'Are you a community builder and wish to build you own community?'

SUB_TITLE_ACCESS_NOT_PART_OF_COMMUNITIES = 'If yes, click on the invitation link you have received.\n\n In case you purchased a membership plan, you would have received an invitation link via email/WhatsApp. Use this link to join your community and get started.'
SUB_TITLE_ACCESS_ONE_PENDING_COMMUNITY = 'Your application to join this community has been submitted. You will have access to community events, chat rooms and member profiles as soon as you are approved.'
SUB_TITLE_ACCESS_ONE_EXPIRED_COMMUNITY = 'Your subscription to %s community has expired. <<Buy a membership plan|route://renew_membership?community_id=%s>> of your choice to regain access to community events, chat rooms and member profiles. Want to leave? do it <<here|route://leave_community?community_id=%s>>.'
SUB_TITLE_ACCESS_MORE_PENDING_COMMUNITIES = 'Your applications to join the following communities have been submitted. You will have access to community events, chat rooms and member profiles as soon as you are approved.'
SUB_TITLE_ACCESS_MORE_EXPIRED_COMMUNITIES = 'Your subscription to following communities has expired. Buy membership plans of your choice to regain access to community events, chat rooms and member profiles.'
SUB_TITLE_ACCESS_MORE_PENDING_ONE_EXPIRED_COMMUNITY = 'Your membership plan for “%s” has expired. You will have access to community events, chat rooms and member profiles as soon as you <<renew your membership|route://renew_membership?community_id=%s>>'
SUB_TITLE_ACCESS_MORE_PENDING_MORE_EXPIRED_COMMUNITIES = 'Your membership plans for multiple communities have expired. You will have access to your community and other awesome features on this app as soon as you renew your memberships.'

SUB_TITLE_2_ACCESS_NOT_PART_OF_COMMUNITIES = 'To get onboarded on this platform to build and grow your community, fill out <<this form|route://browser?link=https://collabmates.app.link/e/3WjswrRfhdb>>'
SUB_TITLE_2_ACCESS_COMMON = '**Usually It takes upto 48 hours to get approved. If you have paid for the membership and in case you are not approved, your payment would be refunded.'

ACCESS_FOOTER = 'Need help? <<Get in touch|route://browser?url=https%3A//wa.me/%2B919971769713%3Ftext%3DI%20need%20help%20in%20joining%20a%20community>>'

CTA_ACCESS_ONE_EXPIRED_COMMUNITY = f'<<CHOOSE MEMBERSHIP PLAN|route://browser?link={web_url}/renewal/%s?renew=true&user_id=%s>>'

CONTEXT_ACCESS_NOT_PART_OF_COMMUNITIES = {
    'success': True,
    'header': HEADER_ACCESS_NOT_PART_OF_COMMUNITIES,
    'header_image': ACCESS_LOCK_ICON,
    'title_1': TITLE_ACCESS_NOT_PART_OF_COMMUNITIES,
    'sub_title_1': SUB_TITLE_ACCESS_NOT_PART_OF_COMMUNITIES,
    'title_2': SECOND_TITLE_ACCESS_NOT_PART_OF_COMMUNITIES,
    'sub_title_2': SUB_TITLE_2_ACCESS_NOT_PART_OF_COMMUNITIES,
    'discover_community': False,
    'footer': ACCESS_FOOTER,
    'access': False
}

CONTEXT_ACCESS_ONE_PENDING_COMMUNITY = {
    'success': True,
    'header': HEADER_ACCESS_ONE_PENDING_COMMUNITY,
    'header_image': ACCESS_HEADER_IMAGE,
    'title_1': TITLE_ACCESS_ONE_PENDING_COMMUNITY,
    'sub_title_1': SUB_TITLE_ACCESS_ONE_PENDING_COMMUNITY,
    'sub_title_2': SUB_TITLE_2_ACCESS_COMMON,
    'footer': ACCESS_FOOTER,
    'access': False
}

CONTEXT_ACCESS_ONE_EXPIRED_COMMUNITY = {
    'success': True,
    'header': HEADER_ACCESS_ONE_EXPIRED_COMMUNITY,
    'header_image': ACCESS_HEADER_IMAGE,
    'title_1': TITLE_ACCESS_ONE_EXPIRED_COMMUNITY,
    'sub_title_1': '',
    'cta': '',
    'footer': ACCESS_FOOTER,
    'access': False
}

CONTEXT_ACCESS_MORE_PENDING_COMMUNITIES = {
    'success': True,
    'header_image': ACCESS_HEADER_IMAGE,
    'title_1': TITLE_ACCESS_MORE_PENDING_COMMUNITIES,
    'sub_title_1': SUB_TITLE_ACCESS_MORE_PENDING_COMMUNITIES,
    'sub_title_2': SUB_TITLE_2_ACCESS_COMMON,
    'footer': ACCESS_FOOTER,
    'access': False
}

CONTEXT_ACCESS_MORE_EXPIRED_COMMUNITIES = {
    'success': True,
    'header_image': ACCESS_HEADER_IMAGE,
    'title_1': TITLE_ACCESS_MORE_EXPIRED_COMMUNITIES,
    'sub_title_1': SUB_TITLE_ACCESS_MORE_PENDING_COMMUNITIES,
    'footer': ACCESS_FOOTER,
    'access': False
}

CONTEXT_ACCESS_MORE_PENDING_ONE_EXPIRED_COMMUNITIES = {
    'success': True,
    'header_image': ACCESS_HEADER_IMAGE,
    'title_1': TITLE_ACCESS_MORE_PENDING_ONE_EXPIRED_COMMUNITIES,
    'sub_title_1': '',
    'sub_title_2': SUB_TITLE_2_ACCESS_COMMON,
    'footer': ACCESS_FOOTER,
    'access': False
}

CONTEXT_ACCESS_MORE_PENDING_MORE_EXPIRED_COMMUNITIES = {
    'success': True,
    'header_image': ACCESS_HEADER_IMAGE,
    'title_1': TITLE_ACCESS_MORE_PENDING_MORE_EXPIRED_COMMUNITIES,
    'sub_title_1': SUB_TITLE_ACCESS_MORE_PENDING_MORE_EXPIRED_COMMUNITIES,
    'sub_title_2': SUB_TITLE_2_ACCESS_COMMON,
    'footer': ACCESS_FOOTER,
    'access': False
}

SUBSCRIPTION_FETCH_API_PATH = "api/subscription/fetch"
