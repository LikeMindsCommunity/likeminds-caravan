#variables
HOURS_24 = 500


chatroom_actions_creator_mute = [

    {
    'id': 1,
    'title': 'Rename chatroom'
    },

   {
    'id': 2,
    'title': 'View participants'
   },

  {
    'id': 3,
    'title': 'Invite'
  },

  {
    'id': 5,
    'title': 'View community'
  },


  {
    'id': 7,
    'title': 'Delete chatroom'
  },

  {
    'id': 8,
    'title': 'Unmute notifications'
  },


]

chatroom_actions_creator_unmute = [

    {
        'id': 1,
        'title': 'Rename chatroom'
    },

    {
        'id': 2,
        'title': 'View participants'
    },

    {
        'id': 3,
        'title': 'Invite'
    },

    {
        'id': 5,
        'title': 'View community'
    },

    {
        'id': 6,
        'title': 'Mute notifications'
    },

    {
        'id': 7,
        'title': 'Delete chatroom'
    },



]

collabcard_action_user_follow_unmute = [



    {
        'id': 2,
        'title': 'View participants'
    },

    {
        'id': 3,
        'title': 'Invite'
    },

    {
        'id': 5,
        'title': 'View community'
    },

    {
        'id': 6,
        'title': 'Mute notifications'
    },

    {
        'id': 9,
        'title': 'Unfollow chatroom'
    },

    {
        'id': 10,
        'title': 'Report'
    }


]



collabcard_action_user_follow_mute = [



    {
        'id': 2,
        'title': 'View participants'
    },

    {
        'id': 3,
        'title': 'Invite'
    },

    {
        'id': 5,
        'title': 'View community'
    },

    {
        'id': 8,
        'title': 'UnMute notifications'
    },

    {
        'id': 9,
        'title': 'Unfollow chatroom'
    },

    {
        'id': 10,
        'title': 'Report'
    }


]


collabcard_action_user_unfollow = [



    {
        'id': 2,
        'title': 'View participants'
    },

    {
        'id': 3,
        'title': 'Invite'
    },

    {
        'id': 5,
        'title': 'View community'
    },

    {
        'id': 4,
        'title': 'Follow chatroom'
    },

    {
        'id': 10,
        'title': 'Report'
    }
]

rename_chatroom = {'id': 1, 'title': 'Rename chatroom'}

view_participants = {'id': 2, 'title': 'View participants'}

invite = {'id': 3, 'title': 'Invite'}

follow_chatroom = {'id': 4, 'title': 'Follow chatroom'}

view_community = {'id': 5, 'title': 'View community'}

mute_notifications = {'id': 6, 'title': 'Mute notifications'}

delete_chatroom = {'id': 7, 'title': 'Delete chatroom'}

unMute_notifications = {'id': 8, 'title': 'UnMute notifications'}

unfollow_chatroom = {'id': 9, 'title': 'Unfollow chatroom'}

report = {'id': 10, 'title': 'Report'}




#get onboarding examples
ONBOARDING_EXAMPLES = [


    {
    "header":"Sample community purposes",
    "sub_header" : "Here are few examples of other communities’ purpose.",
    "title" : "IITD Entrepreneurs in Gurgaon",
    "sub_title":"""Hello everyone, I am a 2012 graduate from electrical engineering. I am running a social media venture based out of Gurgaon. Looking forward to connecting with you all and contribute to this community however I can."""

    },

    {
    "header":"Sample community purposes",
    "sub_header" : "Here are few examples of other communities’ purpose.",
    "title" : "Musicians in Gurgaon",
    "sub_title":"A musician from the Himalayas! Looking for paid opportunities to play percussion (Djembe & Cajon)! I bet your feet won’t stay on the ground for long!  "

    },

    {
    "header":"Sample community purpose",
    "sub_header" : "Here are few examples of other communities’ purpose.",
    "title" : "COVID Hackers",
    "sub_title":"""Hey all, I am a tech entrepreneur from Gurgaon. Looking forward to hacking the COVID times with this tribe and discover fun new "At Home" hobbies 🤟"""

    }

]



MENU = {
    'member' : ['Invite members','View all chat rooms','Member directory','Leave community','Report'],
    'promoter': ['Invite members','View all chat rooms','Member directory','Edit community','Report'],
    'pending_member':['Cancel joining request']
}
