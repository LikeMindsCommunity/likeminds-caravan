from utility.states import email_types
from utility.mail_category_constants import EmailCategories, EmailSubCategories


class EmailMapper:

    mappings = {
        '{}__{}'.format(EmailCategories.CHATROOM, EmailSubCategories.POLL_RESULTS): {
            'location': 'mails/poll_results_announcement.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.DOWNLOAD_APP, EmailSubCategories.REQUEST_ACCEPTED): {
            'location': 'mails/community_confirmation_email.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.DOWNLOAD_APP, EmailSubCategories.DOWNLOAD_DRIP): {
            'location': 'mails/community_confirmation_email_2.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.WELCOME, EmailSubCategories.WELCOME): {
            'location': None,
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.EVENT_REGISTER, EmailSubCategories.PAID_EVENT_CREATED): {
            'location': 'mails/event_comms/paid-event-created.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.EVENT_REGISTER, EmailSubCategories.FREE_EVENT_CREATED): {
            'location': 'mails/event_comms/free-event-created.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.EVENT_REGISTER, EmailSubCategories.PAID_EVENT_REGISTRATION_LAST_CALL): {
            'location': 'mails/event_comms/paid-event-last-call.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.EVENT_REGISTER, EmailSubCategories.FREE_EVENT_REGISTRATION_LAST_CALL): {
            'location': 'mails/event_comms/free-event-last-call.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.EVENT_REGISTER, EmailSubCategories.PAID_EVENT_REGISTRATION_SUCCESSFUL): {
            'location': 'mails/event_comms/paid-event-reg-success.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.EVENT_REGISTER, EmailSubCategories.FREE_EVENT_REGISTRATION_SUCCESSFUL): {
            'location': 'mails/event_comms/free-event-reg-success.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.EVENT_ATTENDANCE, EmailSubCategories.DAY_OF_EVENT): {
            'location': 'mails/event_comms/event-attendance.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.POST_EVENT, EmailSubCategories.EVENT_ATTENDANCE): {
            'location': 'mails/event_comms/post-event-attendees.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.POST_EVENT, EmailSubCategories.EVENT_ATTACHMENTS): {
            'location': 'mails/event_comms/post-event-attachments.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.CREATE_COMMUNITY, EmailSubCategories.DROPOFF): {
            'location': 'mails/cm_onboarding/cm_dropoff_mail_cm_onboarding.html',
            'email_type': email_types.ADMIN_EMAIL
        },

        '{}__{}'.format(EmailCategories.CREATE_COMMUNITY, EmailSubCategories.GETTING_STARTED): {
            'location': 'mails/cm_onboarding/getting_started_cm_onboarding.html',
            'email_type': email_types.ADMIN_EMAIL
        },

        '{}__{}'.format(EmailCategories.CREATE_COMMUNITY, EmailSubCategories.FIRST_EVENT_CREATED): {
            'location': 'mails/cm_onboarding/first_event_creation_cm_onboarding.html',
            'email_type': email_types.ADMIN_EMAIL
        },

        '{}__{}'.format(EmailCategories.CREATE_COMMUNITY, EmailSubCategories.JOIN_FORM_CREATED): {
            'location': 'mails/cm_onboarding/customise_join_form_cm_onboarding.html',
            'email_type': email_types.ADMIN_EMAIL
        },

        '{}__{}'.format(EmailCategories.INVITE_MEMBER, EmailSubCategories.WITH_JOIN_CODE): {
            'location': 'mails/cm_onboarding/invite_members_cm_onboarding.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.ENGAGEMENT, EmailSubCategories.CHATROOM_TAG): {
            'location': 'mails/engagement_mails/tagged_chatroom_not_opened.html',
            'email_type': email_types.COMMUNITY_EMAIL
        },

        '{}__{}'.format(EmailCategories.ENGAGEMENT, EmailSubCategories.DM): {
            'location': 'mails/engagement_mails/dm_chatroom_not_opened.html',
            'email_type': email_types.COMMUNITY_EMAIL
        }
    }

    def get_email_mapping(self, category, subcategory):

        return self.mappings.get('{}__{}'.format(category, subcategory), None)


email_mapper = EmailMapper()
