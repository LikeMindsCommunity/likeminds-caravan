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
        "question_state": 7,
        "tag": "about",
        "value": "[{\"min_chars\": \"50\", \"max_chars\": \"No limit\"}]"
    },
    {
        "id": 50011,
        "question_title": "Your City",
        "value": "",
        "optional": True,
        "question_state": 11,
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
        "value": "[{\"value\": \"Community advocacy\"}, {\"value\": \"Community architecture\"}, {\"value\": \"Community engagement\"}, {\"value\": \"Community growth\"}, {\"value\": \"Community moderation \"}, {\"value\": \"Community platforms and tools management\"}, {\"value\": \"Community product management\"}, {\"value\": \"Community strategy\"}, {\"value\": \"Conflict resolution\"}, {\"value\": \"Content creation \"}, {\"value\": \"Content curation\"}, {\"value\": \"Crisis management and communication\"}, {\"value\": \"Customer support\"}, {\"value\": \"Data analysis\"}, {\"value\": \"Diversity and inclusion\"}, {\"value\": \"Education and training\"}, {\"value\": \"Event planning and management\"}, {\"value\": \"Internal community building\"}, {\"value\": \"Marketing\"}, {\"value\": \"Networking\"}, {\"value\": \"Partnerships and collaboration\"}, {\"value\": \"Social media management\"}, {\"value\": \"Technology\"}, {\"value\": \"Trust & safety\"}, {\"value\": \"User research \"}, {\"value\": \"Volunteer management\"}]",
        "optional": True,
        "can_add_options": True,
        "options_only_for_self": True,
        "question_state": 2,
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
        "is_answer_editable": True,
        "question_state": 0,
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
        "question_state": 8,
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
        "question_state": 8,
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
        "question_state": 8,
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
        "question_state": 12,
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
        "question_state": 1,
        "tag": "basic",
        "value": "[{\"value\": \"Brand ambassador\"}, {\"value\": \"Brand community manager\"}, {\"value\": \"Communications specialist\"}, {\"value\": \"Community advocate\"}, {\"value\": \"Community coach\"}, {\"value\": \"Community consultant\"}, {\"value\": \"Community director\"}, {\"value\": \"Community engagement manager\"}, {\"value\": \"Community manager\"}, {\"value\": \"Community outreach specialist\"}, {\"value\": \"Community strategist\"}, {\"value\": \"Community support specialist\"}, {\"value\": \"Content creator\"}, {\"value\": \"Customer success manager\"}, {\"value\": \"Digital marketing manager\"}, {\"value\": \"Event coordinator\"}, {\"value\": \"Event coordinator \"}, {\"value\": \"Founder\"}, {\"value\": \"Growth hacker\"}, {\"value\": \"Head of community\"}, {\"value\": \"Head of content & community\"}, {\"value\": \"Head of growth\"}, {\"value\": \"Head of technology\"}, {\"value\": \"Moderator\"}, {\"value\": \"Outreach coordinator\"}, {\"value\": \"Product manager\"}, {\"value\": \"Product marketing manager\"}, {\"value\": \"Public relations manager\"}, {\"value\": \"Social media manager\"}, {\"value\": \"Software developer\"}, {\"value\": \"Strategic partnership manager\"}, {\"value\": \"Volunteer coordinator\"}]"
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
        "question_state": 1,
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
        "question_state": 1,
        "tag": "about",
        "value": "[{\"value\": \"Agriculture\"}, {\"value\": \"Automotive\"}, {\"value\": \"Beauty\"}, {\"value\": \"Ecommerce\"}, {\"value\": \"Education\"}, {\"value\": \"Entertainment\"}, {\"value\": \"Finance\"}, {\"value\": \"Fitness\"}, {\"value\": \"Food\"}, {\"value\": \"Gaming\"}, {\"value\": \"Government\"}, {\"value\": \"Healthcare\"}, {\"value\": \"Insurance\"}, {\"value\": \"It/ites\"}, {\"value\": \"Legal\"}, {\"value\": \"Logistics\"}, {\"value\": \"Manufacturing\"}, {\"value\": \"Marketing\"}, {\"value\": \"Music\"}, {\"value\": \"Parenting\"}, {\"value\": \"Photography\"}, {\"value\": \"Real estate\"}, {\"value\": \"Recruitment\"}, {\"value\": \"Retail\"}, {\"value\": \"Saas\"}, {\"value\": \"Social\"}, {\"value\": \"Sports\"}, {\"value\": \"Travel\"}]"
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
        "question_state": 1,
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
        "question_state": 2,
        "tag": "tool_stack",
        "value": "[{\"value\": \"6connect\"}, {\"value\": \"Accelevents\"}, {\"value\": \"Act-on\"}, {\"value\": \"Activecampaign\"}, {\"value\": \"Adobe\"}, {\"value\": \"Ahoyconnect\"}, {\"value\": \"Airmeet\"}, {\"value\": \"Airtable\"}, {\"value\": \"Airtime\"}, {\"value\": \"Aluminati\"}, {\"value\": \"Amplitude\"}, {\"value\": \"Atlassian\"}, {\"value\": \"Aweber\"}, {\"value\": \"Balloon\"}, {\"value\": \"Band\"}, {\"value\": \"Beam\"}, {\"value\": \"Bevy\"}, {\"value\": \"Bizly\"}, {\"value\": \"Bizzabo\"}, {\"value\": \"Boon\"}, {\"value\": \"Bramble\"}, {\"value\": \"Brandwatch\"}, {\"value\": \"Brella\"}, {\"value\": \"Brightest\"}, {\"value\": \"Buddyboss\"}, {\"value\": \"Bunches\"}, {\"value\": \"Butter\"}, {\"value\": \"Buttondown\"}, {\"value\": \"Buzzsumo\"}, {\"value\": \"Campaign monitor\"}, {\"value\": \"Canva\"}, {\"value\": \"Capsule\"}, {\"value\": \"Casa\"}, {\"value\": \"Caveday\"}, {\"value\": \"Cete\"}, {\"value\": \"Chainfuel\"}, {\"value\": \"Chaordix\"}, {\"value\": \"Circle\"}, {\"value\": \"Close\"}, {\"value\": \"Clubhouse\"}, {\"value\": \"Common room\"}, {\"value\": \"Commsor\"}, {\"value\": \"Community\"}, {\"value\": \"Comradery\"}, {\"value\": \"Connect.club\"}, {\"value\": \"Connectplus\"}, {\"value\": \"Constant contact\"}, {\"value\": \"Convertkit\"}, {\"value\": \"Convosight\"}, {\"value\": \"Copper\"}, {\"value\": \"Cosmos\"}, {\"value\": \"Crowdcast\"}, {\"value\": \"Crowded\"}, {\"value\": \"Crowdstack pro\"}, {\"value\": \"Customer.io\"}, {\"value\": \"Cvent\"}, {\"value\": \"Demio\"}, {\"value\": \"Disciple\"}, {\"value\": \"Discord\"}, {\"value\": \"Discourse\"}, {\"value\": \"Distilled\"}, {\"value\": \"Docusaurus\"}, {\"value\": \"Donut\"}, {\"value\": \"Drip\"}, {\"value\": \"Echofin\"}, {\"value\": \"Edition\"}, {\"value\": \"Element\"}, {\"value\": \"Empact\"}, {\"value\": \"Event anywhere\"}, {\"value\": \"Event farm\"}, {\"value\": \"Eventbrite\"}, {\"value\": \"Facebook\"}, {\"value\": \"Figma\"}, {\"value\": \"Filo\"}, {\"value\": \"Flarum\"}, {\"value\": \"Forem\"}, {\"value\": \"Forumbee\"}, {\"value\": \"Frshworks\"}, {\"value\": \"Gather\"}, {\"value\": \"Gatheround\"}, {\"value\": \"Geneva\"}, {\"value\": \"Getresponse\"}, {\"value\": \"Ghost\"}, {\"value\": \"Gitbook\"}, {\"value\": \"Github discussions\"}, {\"value\": \"Gitter\"}, {\"value\": \"Glimpse\"}, {\"value\": \"Glynk\"}, {\"value\": \"Goldcast\"}, {\"value\": \"Gooddata\"}, {\"value\": \"Google\"}, {\"value\": \"Goto\"}, {\"value\": \"Grip\"}, {\"value\": \"Groop\"}, {\"value\": \"Groupapp\"}, {\"value\": \"Grytics\"}, {\"value\": \"Guild\"}, {\"value\": \"Haaartland\"}, {\"value\": \"Habitate\"}, {\"value\": \"Heartbeat\"}, {\"value\": \"Hellohub\"}, {\"value\": \"Heysummit\"}, {\"value\": \"Hi right now\"}, {\"value\": \"Higher logic\"}, {\"value\": \"Hivebrite\"}, {\"value\": \"Hiven\"}, {\"value\": \"Hologram\"}, {\"value\": \"Honeycommb\"}, {\"value\": \"Hootsuite\"}, {\"value\": \"Hopin\"}, {\"value\": \"Hubb\"}, {\"value\": \"Hublio\"}, {\"value\": \"Hubspot\"}, {\"value\": \"Ifttt\"}, {\"value\": \"Inconf\"}, {\"value\": \"Inevent\"}, {\"value\": \"Influitive\"}, {\"value\": \"Insided\"}, {\"value\": \"Insightly\"}, {\"value\": \"Instagram\"}, {\"value\": \"Intercom\"}, {\"value\": \"Intros\"}, {\"value\": \"Invision community\"}, {\"value\": \"Join it\"}, {\"value\": \"Kaapi\"}, {\"value\": \"Keap\"}, {\"value\": \"Keyhole\"}, {\"value\": \"Khoros\"}, {\"value\": \"Kissmetrics\"}, {\"value\": \"Klaviyo\"}, {\"value\": \"Klyk\"}, {\"value\": \"Kommunity\"}, {\"value\": \"Konf\"}, {\"value\": \"Krunch\"}, {\"value\": \"Kumospace\"}, {\"value\": \"Launchpass\"}, {\"value\": \"Likeminds\"}, {\"value\": \"Linkedin\"}, {\"value\": \"Livestorm\"}, {\"value\": \"Localist\"}, {\"value\": \"Locals\"}, {\"value\": \"Looker\"}, {\"value\": \"Lounjee\"}, {\"value\": \"Lowdown\"}, {\"value\": \"Luma\"}, {\"value\": \"Mailchimp\"}, {\"value\": \"Mailjet\"}, {\"value\": \"Make\"}, {\"value\": \"Marketo\"}, {\"value\": \"Matomo\"}, {\"value\": \"Mattermost\"}, {\"value\": \"Meeting machine\"}, {\"value\": \"Meeting place\"}, {\"value\": \"Meetsy\"}, {\"value\": \"Meetup\"}, {\"value\": \"Memberful\"}, {\"value\": \"Memberspace\"}, {\"value\": \"Memberstack\"}, {\"value\": \"Mention\"}, {\"value\": \"Mesh\"}, {\"value\": \"Micepad\"}, {\"value\": \"Mighty networks\"}, {\"value\": \"Mixaba\"}, {\"value\": \"Mixily\"}, {\"value\": \"Mmhmm\"}, {\"value\": \"Mobilize\"}, {\"value\": \"Momo board\"}, {\"value\": \"N8n\"}, {\"value\": \"Nationbuilder\"}, {\"value\": \"Nimble\"}, {\"value\": \"Nodebb\"}, {\"value\": \"Notion\"}, {\"value\": \"Octo\"}, {\"value\": \"Omnisend\"}, {\"value\": \"On24\"}, {\"value\": \"Onlyfans\"}, {\"value\": \"Open social\"}, {\"value\": \"Oracle\"}, {\"value\": \"Orbiit\"}, {\"value\": \"Orbit\"}, {\"value\": \"Orbit\"}, {\"value\": \"Overgroups\"}, {\"value\": \"Owntrail for communities\"}, {\"value\": \"Panion\"}, {\"value\": \"Pardot\"}, {\"value\": \"Parlor\"}, {\"value\": \"Pathable\"}, {\"value\": \"Patreon\"}, {\"value\": \"Peerboard\"}, {\"value\": \"Personify\"}, {\"value\": \"Pico\"}, {\"value\": \"Pipedrive\"}, {\"value\": \"Playgroup\"}, {\"value\": \"Plush forums\"}, {\"value\": \"Podia\"}, {\"value\": \"Postman\"}, {\"value\": \"Potion\"}, {\"value\": \"Quip\"}, {\"value\": \"Rally\"}, {\"value\": \"Reach.live\"}, {\"value\": \"Read the docs\"}, {\"value\": \"Readme\"}, {\"value\": \"Reciprocity\"}, {\"value\": \"Redash\"}, {\"value\": \"Reddit\"}, {\"value\": \"Redocly\"}, {\"value\": \"Remo\"}, {\"value\": \"Revue\"}, {\"value\": \"Rocket.chat\"}, {\"value\": \"Run the world\"}, {\"value\": \"Salesforce\"}, {\"value\": \"Savannah hq\"}, {\"value\": \"Scalegrowth\"}, {\"value\": \"Sched\"}, {\"value\": \"Sendinblue\"}, {\"value\": \"Sense chat\"}, {\"value\": \"Sequel\"}, {\"value\": \"Shindig\"}, {\"value\": \"Sidebar\"}, {\"value\": \"Sinespace\"}, {\"value\": \"Slack\"}, {\"value\": \"Slides\"}, {\"value\": \"Snapchat\"}, {\"value\": \"Space\"}, {\"value\": \"Spacialchat\"}, {\"value\": \"Sparkly\"}, {\"value\": \"Splash\"}, {\"value\": \"Sproutsocial\"}, {\"value\": \"Stack overflow\"}, {\"value\": \"Streamyard\"}, {\"value\": \"Substack\"}, {\"value\": \"Sutra\"}, {\"value\": \"Swagger\"}, {\"value\": \"Swoogo\"}, {\"value\": \"Tableau\"}, {\"value\": \"Tame\"}, {\"value\": \"Tapatalk\"}, {\"value\": \"Tapbots\"}, {\"value\": \"Tchop\"}, {\"value\": \"Teamland\"}, {\"value\": \"Telegram\"}, {\"value\": \"Tevent\"}, {\"value\": \"The watercooler\"}, {\"value\": \"Threado\"}, {\"value\": \"Tiktok\"}, {\"value\": \"Tito\"}, {\"value\": \"Toasty\"}, {\"value\": \"Toky woky\"}, {\"value\": \"Topia\"}, {\"value\": \"Toucan\"}, {\"value\": \"Touchcast\"}, {\"value\": \"Tray.io\"}, {\"value\": \"Tribe.\"}, {\"value\": \"Tulula\"}, {\"value\": \"Tweetdeck\"}, {\"value\": \"Twist\"}, {\"value\": \"Twitch\"}, {\"value\": \"Twitter\"}, {\"value\": \"Ubu\"}, {\"value\": \"Ugenie\"}, {\"value\": \"Una\"}, {\"value\": \"Unlock\"}, {\"value\": \"Upstream\"}, {\"value\": \"Vanilla\"}, {\"value\": \"Vbulletin\"}, {\"value\": \"Verint\"}, {\"value\": \"Vero\"}, {\"value\": \"Vfairs\"}, {\"value\": \"Viafoura\"}, {\"value\": \"Vibely\"}, {\"value\": \"Videoask\"}, {\"value\": \"Vimeo\"}, {\"value\": \"Vito\"}, {\"value\": \"Voiceblasts\"}, {\"value\": \"Warmintro\"}, {\"value\": \"Waves\"}, {\"value\": \"Webex\"}, {\"value\": \"Webinarjam\"}, {\"value\": \"Website toolbox\"}, {\"value\": \"Welcome\"}, {\"value\": \"Whatsapp\"}, {\"value\": \"Whereby\"}, {\"value\": \"Wonder\"}, {\"value\": \"Woopra\"}, {\"value\": \"Workoutloud\"}, {\"value\": \"Xenforo\"}, {\"value\": \"Youtube\"}, {\"value\": \"Zapier\"}, {\"value\": \"Zapnito\"}, {\"value\": \"Zelos\"}, {\"value\": \"Zendesk\"}, {\"value\": \"Zoho\"}, {\"value\": \"Zoom\"}, {\"value\": \"Zulip\"}]"
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
        "question_state": 2,
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
        "question_state": 2,
        "tag": "reach_out_to_me",
        "value": "[{\"value\": \"Advisory role\"}, {\"value\": \"Brainstorming\"}, {\"value\": \"Coaching\"}, {\"value\": \"Consultation\"}, {\"value\": \"Freelancing\"}, {\"value\": \"I am hiring\"}, {\"value\": \"I am open to hire\"}, {\"value\": \"Mentoring\"}, {\"value\": \"Networking\"}, {\"value\": \"Training\"}, {\"value\": \"Workshops\"}]"
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
        "question_state": 8,
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
        "question_state": 8,
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
        "question_state": 8,
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
