import time

from togther.models import (ModelUtilities, communityQuestions, questionFilters, communityAnswers, Community)
from collabmates_api.community.community_impl import CommunityHelper

COMMUNITY_ID = None
USER_ID = None

REPLACE_QUESTION_OPTIONS = {
    '50020': {
        'Moderation': 'Community Moderation',
        'Events': 'Event Planning and Management',
        'Strategy': 'Community Strategy',
        'Data Analytics': 'Data Analysis',
        'Training and Development': 'Education and Training',
        'Engagement': 'Community Engagement'
    }
}

CREATE_OR_UPDATE_QUESTIONS_LIST = [
    {
        "id": 50018,
        "is_hidden": True,
        "field": False,
        "tag": None,
        "rank": 1
    },
    {
        "id": 48228,
        "is_hidden": True,
        "field": False,
        "tag": None,
        "rank": 1
    },
    {
        "id": 50021,
        "is_hidden": True,
        "field": False,
        "tag": None,
        "rank": 1
    },
    {
        "id": 50022,
        "is_hidden": True,
        "field": False,
        "tag": None,
        "rank": 1
    },
    {
        "can_add_options": False,
        "field": False,
        "help_text": "Tell us about yourself",
        "id": 48206,
        "image_url": None,
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": False,
        "question_title": "About You",
        "rank": 0,
        "state": 7,
        "tag": "about",
        "value": "[{\"min_chars\": \"50\", \"max_chars\": \"No limit\"}]"
    },
    {
        "id": 50011,
        "question_title": "Your City",
        "value": "",
        "optional": True,
        "state": 11,
        "is_answer_editable": True,
        "help_text": "Select City",
        "is_hidden": False,
        "field": True,
        "tag": "basic",
        "rank": 3
    },
    {
        "id": 50020,
        "question_title": "Area of Specialization",
        "value": "[{\"value\": \"Technology\"}, {\"value\": \"Community Strategy\"}, {\"value\": \"Community Growth\"}, {\"value\": \"Community Engagement\"}, {\"value\": \"Community Advocacy\"}, {\"value\": \"Diversity and Inclusion\"}, {\"value\": \"Community Product Management\"}, {\"value\": \"Data Analysis\"}, {\"value\": \"Content Curation\"}, {\"value\": \"Event Planning and Management\"}, {\"value\": \"Internal Community Building\"}, {\"value\": \"Education and Training\"}, {\"value\": \"User Research \"}, {\"value\": \"Crisis Management and Communication\"}, {\"value\": \"Customer Support\"}, {\"value\": \"Volunteer Management\"}, {\"value\": \"Networking\"}, {\"value\": \"Marketing\"}, {\"value\": \"Content Creation \"}, {\"value\": \"Community Moderation \"}, {\"value\": \"Trust & Safety\"}, {\"value\": \"Social Media Management\"}, {\"value\": \"Conflict Resolution\"}, {\"value\": \"Partnerships and Collaboration\"}, {\"value\": \"Community Architecture\"}, {\"value\": \"Community Platforms and Tools Management\"}]",
        "optional": True,
        "can_add_options": True,
        "options_only_for_self": True,
        "community_id": 49751,
        "state": 2,
        "is_answer_editable": True,
        "help_text": "Select",
        "is_hidden": False,
        "field": False,
        "tag": "basic",
        "rank": 4
    },
    {
        "id": 50017,
        "question_title": "Organisation/Community Name",
        "value": None,
        "optional": False,
        "community_id": 49751,
        "is_answer_editable": True,
        "state": 0,
        "help_text": "Company or community you are associated with",
        "is_hidden": False,
        "field": False,
        "tag": "basic",
        "rank": 1
    },
    {
        "id": 50014,
        "question_title": "Your LinkedIn Profile URL",
        "value": "[{\"profile_platform\": \"LinkedIn\", \"answer_privacy\": \"Public\"}]",
        "optional": True,
        "state": 8,
        "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/LinkedIn.png",
        "help_text": "Type URL",
        "is_hidden": False,
        "is_answer_editable": True,
        "field": True,
        "tag": "socials",
        "rank": 1
    },
    {
        "id": 50015,
        "question_title": "Your Instagram username",
        "value": "[{\"profile_platform\": \"Instagram\", \"answer_privacy\": \"Public\"}]",
        "optional": True,
        "state": 8,
        "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Insta.png",
        "help_text": "@username",
        "is_hidden": False,
        "field": True,
        "is_answer_editable": True,
        "tag": "socials",
        "rank": 2
    },
    {
        "id": 50016,
        "question_title": "Your Twitter handle",
        "value": "[{\"profile_platform\": \"Twitter\", \"answer_privacy\": \"Public\"}]",
        "optional": True,
        "state": 8,
        "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Twitter.png",
        "help_text": "@handle",
        "is_answer_editable": True,
        "is_hidden": False,
        "field": True,
        "tag": "socials",
        "rank": 3
    },
    {
        "can_add_options": False,
        "field": False,
        "help_text": "Enter your full name",
        "image_url": None,
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": False,
        "options_only_for_self": False,
        "question_title": "Your Name",
        "rank": 0,
        "state": 12,
        "tag": "basic",
        "value": None
    },
    {
        "can_add_options": True,
        "field": False,
        "help_text": "Your role at your organisation/community",
        "image_url": None,
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": False,
        "options_only_for_self": True,
        "question_title": "Designation/Role",
        "rank": 2,
        "state": 1,
        "tag": "basic",
        "value": "[{\"value\": \"Brand Ambassador\"}, {\"value\": \"Head of Growth\"}, {\"value\": \"Head of Technology\"}, {\"value\": \"Growth Hacker\"}, {\"value\": \"Event Coordinator \"}, {\"value\": \"Strategic Partnership Manager\"}, {\"value\": \"Community Consultant\"}, {\"value\": \"Social Media Manager\"}, {\"value\": \"Outreach Coordinator\"}, {\"value\": \"Founder\"}, {\"value\": \"Volunteer Coordinator\"}, {\"value\": \"Brand Community Manager\"}, {\"value\": \"Product Marketing Manager\"}, {\"value\": \"Community Director\"}, {\"value\": \"Community Outreach Specialist\"}, {\"value\": \"Community Advocate\"}, {\"value\": \"Head of Content & Community\"}, {\"value\": \"Community Manager\"}, {\"value\": \"Customer Success Manager\"}, {\"value\": \"Community Strategist\"}, {\"value\": \"Communications Specialist\"}, {\"value\": \"Software Developer\"}, {\"value\": \"Content Creator\"}, {\"value\": \"Head of Community\"}, {\"value\": \"Public Relations Manager\"}, {\"value\": \"Digital Marketing Manager\"}, {\"value\": \"Community Engagement Manager\"}, {\"value\": \"Moderator\"}, {\"value\": \"Event Coordinator\"}, {\"value\": \"Community Coach\"}, {\"value\": \"Product Manager\"}, {\"value\": \"Community Support Specialist\"}]"
    },
    {
        "can_add_options": False,
        "field": False,
        "help_text": "Select",
        "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/people.png",
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": False,
        "question_title": "Scale of Community",
        "rank": 1,
        "state": 1,
        "tag": "about",
        "value": "[{\"value\": \"0-100\"}, {\"value\": \"100-500\"}, {\"value\": \"500-1k\"}, {\"value\": \"1k-5k\"}, {\"value\": \"5k-10k\"}, {\"value\": \"10k-50k\"}, {\"value\": \"50k-100k\"}, {\"value\": \"100k+\"}]"
    },
    {
        "can_add_options": False,
        "field": False,
        "help_text": "Select",
        "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/company%403x.png",
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": False,
        "question_title": "Industry",
        "rank": 2,
        "state": 1,
        "tag": "about",
        "value": "[{\"value\": \"Healthcare\"}, {\"value\": \"Finance\"}, {\"value\": \"Education\"}, {\"value\": \"Retail\"}, {\"value\": \"Real Estate\"}, {\"value\": \"Government\"}, {\"value\": \"Manufacturing\"}, {\"value\": \"Ecommerce\"}, {\"value\": \"Recruitment\"}, {\"value\": \"Travel\"}, {\"value\": \"Entertainment\"}, {\"value\": \"Food\"}, {\"value\": \"IT/ITES\"}, {\"value\": \"Insurance\"}, {\"value\": \"Legal\"}, {\"value\": \"Sports\"}, {\"value\": \"Marketing\"}, {\"value\": \"Agriculture\"}, {\"value\": \"Music\"}, {\"value\": \"Gaming\"}, {\"value\": \"Automotive\"}, {\"value\": \"Beauty\"}, {\"value\": \"Logistics\"}, {\"value\": \"Fitness\"}, {\"value\": \"Photography\"}, {\"value\": \"Parenting\"}, {\"value\": \"Social\"}, {\"value\": \"SaaS\"}]"
    },
    {
        "can_add_options": False,
        "field": False,
        "help_text": "Select",
        "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/resident+since%403x.png",
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": False,
        "question_title": "Community Experience",
        "rank": 3,
        "state": 1,
        "tag": "about",
        "value": "[{\"value\": \"0-1 years\"}, {\"value\": \"1-3 years\"}, {\"value\": \"5-7 years\"}, {\"value\": \"7-10 years\"}, {\"value\": \"10-15 years\"}, {\"value\": \"15-20 years\"}, {\"value\": \"20 years +\"}]"
    },
    {
        "can_add_options": True,
        "field": False,
        "help_text": "Select",
        "image_url": None,
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": True,
        "question_title": "Tool Stack",
        "rank": 0,
        "state": 2,
        "tag": "tool_stack",
        "value": "[{\"value\": \"Grytics\"}, {\"value\": \"Read The Docs\"}, {\"value\": \"vFairs\"}, {\"value\": \"Tapatalk\"}, {\"value\": \"Reddit\"}, {\"value\": \"Discourse\"}, {\"value\": \"Glynk\"}, {\"value\": \"mixaba\"}, {\"value\": \"Flarum\"}, {\"value\": \"sequel\"}, {\"value\": \"donut\"}, {\"value\": \"NationBuilder\"}, {\"value\": \"Make\"}, {\"value\": \"GoTo\"}, {\"value\": \"forumbee\"}, {\"value\": \"mailjet\"}, {\"value\": \"tray.io\"}, {\"value\": \"Waves\"}, {\"value\": \"tevent\"}, {\"value\": \"Kaapi\"}, {\"value\": \"hubb\"}, {\"value\": \"Higher Logic\"}, {\"value\": \"matomo\"}, {\"value\": \"Personify\"}, {\"value\": \"UNA\"}, {\"value\": \"Klyk\"}, {\"value\": \"WhatsApp\"}, {\"value\": \"Event Farm\"}, {\"value\": \"Gatheround\"}, {\"value\": \"GoodData\"}, {\"value\": \"tame\"}, {\"value\": \"mesh\"}, {\"value\": \"threado\"}, {\"value\": \"GetResponse\"}, {\"value\": \"Join It\"}, {\"value\": \"Bunches\"}, {\"value\": \"Playgroup\"}, {\"value\": \"podia\"}, {\"value\": \"Memberstack\"}, {\"value\": \"Geneva\"}, {\"value\": \"Memberful\"}, {\"value\": \"shindig\"}, {\"value\": \"YouTube\"}, {\"value\": \"commsor\"}, {\"value\": \"Notion\"}, {\"value\": \"INTERCOM\"}, {\"value\": \"Marketo\"}, {\"value\": \"kissmetrics\"}, {\"value\": \"BuzzSumo\"}, {\"value\": \"IFTTT\"}, {\"value\": \"Keyhole\"}, {\"value\": \"ActiveCampaign\"}, {\"value\": \"HeySummit\"}, {\"value\": \"Revue\"}, {\"value\": \"Docusaurus\"}, {\"value\": \"Hootsuite\"}, {\"value\": \"tableau\"}, {\"value\": \"Hublio\"}, {\"value\": \"customer.io\"}, {\"value\": \"Substack\"}, {\"value\": \"Plush Forums\"}, {\"value\": \"vibely\"}, {\"value\": \"inSided\"}, {\"value\": \"COSMOS\"}, {\"value\": \"Intros\"}, {\"value\": \"bizly\"}, {\"value\": \"PeerBoard\"}, {\"value\": \"influitive\"}, {\"value\": \"mention\"}, {\"value\": \"Potion\"}, {\"value\": \"Caveday\"}, {\"value\": \"groop\"}, {\"value\": \"Sense Chat\"}, {\"value\": \"Website Toolbox\"}, {\"value\": \"xenForo\"}, {\"value\": \"crowded\"}, {\"value\": \"Meeting Place\"}, {\"value\": \"Gather\"}, {\"value\": \"pathable\"}, {\"value\": \"VoiceBlasts\"}, {\"value\": \"micepad\"}, {\"value\": \"boon\"}, {\"value\": \"Swagger\"}, {\"value\": \"sinespace\"}, {\"value\": \"ScaleGrowth\"}, {\"value\": \"GroupApp\"}, {\"value\": \"lounjee\"}, {\"value\": \"keap\"}, {\"value\": \"Guild\"}, {\"value\": \"mobilize\"}, {\"value\": \"salesforce\"}, {\"value\": \"Brella\"}, {\"value\": \"Disciple\"}, {\"value\": \"splash\"}, {\"value\": \"Redash\"}, {\"value\": \"parlor\"}, {\"value\": \"Hi Right Now\"}, {\"value\": \"BAND\"}, {\"value\": \"Google\"}, {\"value\": \"Warmintro\"}, {\"value\": \"Empact\"}, {\"value\": \"Heartbeat\"}, {\"value\": \"VERINT\"}, {\"value\": \"zapier\"}, {\"value\": \"Distilled\"}, {\"value\": \"Gitter\"}, {\"value\": \"Livestorm\"}, {\"value\": \"ReadMe\"}, {\"value\": \"viafoura\"}, {\"value\": \"Toasty\"}, {\"value\": \"PICO\"}, {\"value\": \"WorkOutLoud\"}, {\"value\": \"Hiven\"}, {\"value\": \"6Connect\"}, {\"value\": \"Kommunity\"}, {\"value\": \"accelevents\"}, {\"value\": \"Brandwatch\"}, {\"value\": \"Glimpse\"}, {\"value\": \"Butter\"}, {\"value\": \"drip\"}, {\"value\": \"Airtable\"}, {\"value\": \"SpacialChat\"}, {\"value\": \"klaviyo\"}, {\"value\": \"Github Discussions\"}, {\"value\": \"element\"}, {\"value\": \"BuddyBoss\"}, {\"value\": \"Crowdcast\"}, {\"value\": \"mmhmm\"}, {\"value\": \"Tito\"}, {\"value\": \"Community\"}, {\"value\": \"Vito\"}, {\"value\": \"Wonder\"}, {\"value\": \"ConnectPlus\"}, {\"value\": \"lowdown\"}, {\"value\": \"pardot\"}, {\"value\": \"InEvent\"}, {\"value\": \"luma\"}, {\"value\": \"Konf\"}, {\"value\": \"Swoogo\"}, {\"value\": \"Chaordix\"}, {\"value\": \"Sched\"}, {\"value\": \"Ubu\"}, {\"value\": \"OnlyFans\"}, {\"value\": \"Invision Community\"}, {\"value\": \"hologram\"}, {\"value\": \"Bramble\"}, {\"value\": \"ButtonDown\"}, {\"value\": \"Snapchat\"}, {\"value\": \"Run The World\"}, {\"value\": \"Circle\"}, {\"value\": \"Twitter\"}, {\"value\": \"ConvertKit\"}, {\"value\": \"Airmeet\"}, {\"value\": \"balloon\"}, {\"value\": \"brightest\"}, {\"value\": \"Inconf\"}, {\"value\": \"convosight\"}, {\"value\": \"LikeMinds\"}, {\"value\": \"LaunchPass\"}, {\"value\": \"Bevy\"}, {\"value\": \"locals\"}, {\"value\": \"Toucan\"}, {\"value\": \"Tapbots\"}, {\"value\": \"tribe.\"}, {\"value\": \"Topia\"}, {\"value\": \"echofin\"}, {\"value\": \"Toky Woky\"}, {\"value\": \"GitBook\"}, {\"value\": \"AhoyConnect\"}, {\"value\": \"Facebook\"}, {\"value\": \"hivebrite\"}, {\"value\": \"tulula\"}, {\"value\": \"Grip\"}, {\"value\": \"localist\"}, {\"value\": \"omnisend\"}, {\"value\": \"MemberSpace\"}, {\"value\": \"beam\"}, {\"value\": \"Khoros\"}, {\"value\": \"Goldcast\"}, {\"value\": \"Sidebar\"}, {\"value\": \"The Watercooler\"}, {\"value\": \"Meetup\"}, {\"value\": \"Common Room\"}, {\"value\": \"Telegram\"}, {\"value\": \"Honeycommb\"}, {\"value\": \"mixily\"}, {\"value\": \"Instagram\"}, {\"value\": \"act-on\"}, {\"value\": \"Mighty Networks\"}, {\"value\": \"woopra\"}, {\"value\": \"reciprocity\"}, {\"value\": \"haaartland\"}, {\"value\": \"remo\"}, {\"value\": \"nimble\"}, {\"value\": \"Comradery\"}, {\"value\": \"Ugenie\"}, {\"value\": \"OwnTrail for Communities\"}, {\"value\": \"Meetsy\"}, {\"value\": \"vero\"}, {\"value\": \"Casa\"}, {\"value\": \"hopin\"}, {\"value\": \"Rally\"}, {\"value\": \"airtime\"}, {\"value\": \"KUMOSPACE\"}, {\"value\": \"Twist\"}, {\"value\": \"Hubspot\"}, {\"value\": \"Atlassian\"}, {\"value\": \"Panion\"}, {\"value\": \"Reach.Live\"}, {\"value\": \"Slack\"}, {\"value\": \"ghost\"}, {\"value\": \"Quip\"}, {\"value\": \"Campaign Monitor\"}, {\"value\": \"zoho\"}, {\"value\": \"Connect.Club\"}, {\"value\": \"insightly\"}, {\"value\": \"zoom\"}, {\"value\": \"meeting machine\"}, {\"value\": \"Capsule\"}, {\"value\": \"Chainfuel\"}, {\"value\": \"n8n\"}, {\"value\": \"Habitate\"}, {\"value\": \"Amplitude\"}, {\"value\": \"Close\"}, {\"value\": \"OverGroups\"}, {\"value\": \"Constant Contact\"}, {\"value\": \"WebinarJam\"}, {\"value\": \"copper\"}, {\"value\": \"octo\"}, {\"value\": \"eventbrite\"}, {\"value\": \"Sparkly\"}, {\"value\": \"Teamland\"}, {\"value\": \"Filo\"}, {\"value\": \"Upstream\"}, {\"value\": \"LinkedIn\"}, {\"value\": \"Demio\"}, {\"value\": \"Sutra\"}, {\"value\": \"unlock\"}, {\"value\": \"mailchimp\"}, {\"value\": \"zelos\"}, {\"value\": \"Touchcast\"}, {\"value\": \"twitch\"}, {\"value\": \"pipedrive\"}, {\"value\": \"Vanilla\"}, {\"value\": \"Savannah HQ\"}, {\"value\": \"cete\"}, {\"value\": \"tchop\"}, {\"value\": \"krunch\"}, {\"value\": \"Looker\"}, {\"value\": \"Zulip\"}, {\"value\": \"Discord\"}, {\"value\": \"StreamYard\"}, {\"value\": \"Whereby\"}, {\"value\": \"HelloHub\"}, {\"value\": \"sproutsocial\"}, {\"value\": \"Orbit\"}, {\"value\": \"AWeber\"}, {\"value\": \"ON24\"}, {\"value\": \"Mattermost\"}, {\"value\": \"Bizzabo\"}, {\"value\": \"Event Anywhere\"}, {\"value\": \"space\"}, {\"value\": \"TweetDeck\"}, {\"value\": \"rocket.chat\"}, {\"value\": \"zapnito\"}, {\"value\": \"MOMO Board\"}, {\"value\": \"patreon\"}, {\"value\": \"Oracle\"}, {\"value\": \"zendesk\"}, {\"value\": \"vBulletin\"}, {\"value\": \"Crowdstack Pro\"}, {\"value\": \"VideoAsk\"}, {\"value\": \"Redocly\"}, {\"value\": \"Stack Overflow\"}, {\"value\": \"welcome\"}, {\"value\": \"clubhouse\"}, {\"value\": \"TikTok\"}, {\"value\": \"Postman\"}, {\"value\": \"NodeBB\"}, {\"value\": \"Edition\"}, {\"value\": \"Orbiit\"}, {\"value\": \"Forem\"}, {\"value\": \"cvent\"}, {\"value\": \"webex\"}, {\"value\": \"sendinblue\"}, {\"value\": \"frshworks\"}, {\"value\": \"Slides\"}, {\"value\": \"open social\"}, {\"value\": \"Aluminati\"}, {\"value\": \"vimeo\"}, {\"value\": \"Adobe\"}]"
    },
    {
        "can_add_options": True,
        "field": False,
        "help_text": "Select",
        "image_url": None,
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": True,
        "question_title": "Interest Area",
        "rank": 0,
        "state": 2,
        "tag": "interest_area",
        "value": "[{\"value\": \"Technology\"}, {\"value\": \"Community Strategy\"}, {\"value\": \"Community Growth\"}, {\"value\": \"Community Engagement\"}, {\"value\": \"Community Advocacy\"}, {\"value\": \"Diversity and Inclusion\"}, {\"value\": \"Community Product Management\"}, {\"value\": \"Data Analysis\"}, {\"value\": \"Content Curation\"}, {\"value\": \"Event Planning and Management\"}, {\"value\": \"Internal Community Building\"}, {\"value\": \"Education and Training\"}, {\"value\": \"User Research \"}, {\"value\": \"Crisis Management and Communication\"}, {\"value\": \"Customer Support\"}, {\"value\": \"Volunteer Management\"}, {\"value\": \"Networking\"}, {\"value\": \"Marketing\"}, {\"value\": \"Content Creation \"}, {\"value\": \"Community Moderation \"}, {\"value\": \"Trust & Safety\"}, {\"value\": \"Social Media Management\"}, {\"value\": \"Conflict Resolution\"}, {\"value\": \"Partnerships and Collaboration\"}, {\"value\": \"Community Architecture\"}, {\"value\": \"Community Platforms and Tools Management\"}]"
    },
    {
        "can_add_options": False,
        "field": False,
        "help_text": "Select",
        "image_url": None,
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": False,
        "question_title": "Reach out to me for",
        "rank": 0,
        "state": 2,
        "tag": "reach_out_to_me",
        "value": "[{\"value\": \"Freelancing\"}, {\"value\": \"I am hiring\"}, {\"value\": \"Training\"}, {\"value\": \"I am open to hire\"}, {\"value\": \"Brainstorming\"}, {\"value\": \"Coaching\"}, {\"value\": \"Mentoring\"}, {\"value\": \"Workshops\"}, {\"value\": \"Networking\"}, {\"value\": \"Advisory Role\"}]"
    },
    {
        "can_add_options": False,
        "field": False,
        "help_text": "Type URL",
        "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Website.png",
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": False,
        "question_title": "Your Website URL",
        "rank": 0,
        "state": 8,
        "tag": "socials",
        "value": "[{\"profile_platform\":\"Others\",\"answer_privacy\":\"Public\"}]"
    },
    {
        "can_add_options": False,
        "field": False,
        "help_text": "Type URL",
        "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Youtube.png",
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": False,
        "question_title": "Your YouTube URL",
        "rank": 4,
        "state": 8,
        "tag": "socials",
        "value": "[{\"profile_platform\":\"Others\",\"answer_privacy\":\"Public\"}]"
    },
    {
        "can_add_options": False,
        "field": False,
        "help_text": "Type URL",
        "image_url": "https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/files/utilities/Substack+(1).png",
        "is_answer_editable": True,
        "is_compulsory": False,
        "is_hidden": False,
        "optional": True,
        "options_only_for_self": False,
        "question_title": "Your Substack URL",
        "rank": 5,
        "state": 8,
        "tag": "socials",
        "value": "[{\"profile_platform\":\"Others\",\"answer_privacy\":\"Public\"}]"
    }
]


def replace_options_of_questions():
    print('Replacing question options')

    for question_id, replace_dict in REPLACE_QUESTION_OPTIONS.items():
        question_instance = ModelUtilities.get_model_filter(communityQuestions, {'community_id': COMMUNITY_ID,
                                                                                 'id': question_id}).first()

        if not question_instance:
            continue

        for old_val, new_val in replace_dict.items():
            print(f'Replacing {old_val} with {new_val}')
            filter_dict = {
                'question': question_instance,
                'community': COMMUNITY_ID,
                'question_answer__contains': old_val
            }

            answers_filter = ModelUtilities.get_model_filter(communityAnswers, filter_dict)

            for answer_instance in answers_filter:
                old_answer = answer_instance.question_answer
                new_answer = old_answer.replace(old_val, new_val)
                answer_instance.question_answer = new_answer
                answer_instance.save()

            filter_dict = {
                'question': question_instance,
                'community': COMMUNITY_ID,
                'filter__contains': old_val
            }

            question_filters = ModelUtilities.get_model_filter(questionFilters, filter_dict)

            for question_filter in question_filters:
                old_answer = question_filter.filter
                new_answer = old_answer.replace(old_val, new_val)
                question_filter.filter = new_answer
                question_filter.save()


def create_or_update_questions():
    new_questions_list = []

    community_instance = ModelUtilities.get_model_instance_or_none(Community, COMMUNITY_ID)

    if not community_instance:
        return

    print('Creating or updating questions!')

    for question_dict in CREATE_OR_UPDATE_QUESTIONS_LIST:

        if not question_dict.get('id'):
            new_questions_list.append(question_dict)

        print(f"Updating question having question id {question_dict.get('id')}!")

        question_filter = ModelUtilities.get_model_filter(communityQuestions, {'id': question_dict.get('id'),
                                                                               'community': COMMUNITY_ID})

        if not question_filter:
            print(f"No question found corresponding to {question_dict.get('id')} in {COMMUNITY_ID}!")
            continue

        del question_dict['id']

        question_filter.update(**question_dict)

    # Create new questions
    CommunityHelper.create_new_community_questions(community_instance, new_questions_list, USER_ID)


start = time.time()
print('Starting the script!')
create_or_update_questions()
replace_options_of_questions()
print('Script completed in', time.time() - start)
