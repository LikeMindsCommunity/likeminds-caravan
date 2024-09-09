import requests, time

base_url = "https://auth.likeminds.community"
api_key = "f9368ac1-e3cb-42cf-8e6b-fc82c92b9507"
uuid_prefix = "sdk-user-" # sdk/initiate user unique id & name

# Post IDs for which we want to like and comment
post_ids = [
    "66deb6abfbd5bf9f1eef34f3",     # user e - 1000 likes
    "66deb6aa21b6e5613afb97e7",     # user e - 1000 comments
    "66deb68908a35ae09a18b66d",     # user d - 100 likes
    "66deb68821b6e5613afb97e5",     # user d - 100 comments
]

# Get auth token against a uuid using sdk/initiate API
def get_auth_token_from_uuid(uuid):

    initiate_url = base_url + "/sdk/initiate"
    headers = {"x-api-key": api_key}
    initiate_response = requests.post(initiate_url, json={"uuid": uuid}, headers=headers)
    
    if initiate_response.status_code == 200:
        auth_token = initiate_response.json().get("data", {}).get("access_token")
        return auth_token
    else:
        print(f"Failed to initiate for uuid: {uuid} | {initiate_response.json()}")
        return None

# Fetch the universal feed | Needs an auth token
def feed_universal(auth_token):

    if auth_token:
        # Step 2: Call the GET API to fetch the universal feed
        feed_url = base_url + "/feed/universal"
        headers = {"Authorization": auth_token}
        params = {"page_size": 50}
        
        feed_response = requests.get(feed_url, headers=headers, params=params)
        
        # Check if the GET request was successful
        if feed_response.status_code == 200:
            posts = feed_response.json().get("data", {}).get("posts", [])
            
            # Step 3: Iterate over the posts and print them
            for post in posts:
                print(post)
        else:
            print(f"Failed to fetch feed: {feed_response.status_code}")
    else:
        print("Failed to retrieve access token")


# Like a post N times using N different users with delay of 500 ms | Needs a Post Id 
def like_N_times(N, post_id):

    # Iterate for N times
    for i in range(N):
        uuid = uuid_prefix + str(i)
        auth_token = get_auth_token_from_uuid(uuid)
        
        if auth_token:
            like_post(auth_token, post_id)
        
        time.sleep(0.5)

    print(f"Post {post_id} liked {N} times")


# Comment on a post N times using N different users with delay of 500 ms | Needs a Post Id
def comment_N_times(N, post_id):

    # Iterate for N times
    for i in range(N):
        uuid = uuid_prefix + str(i)
        auth_token = get_auth_token_from_uuid(uuid)
        
        if auth_token:
            comment_post(auth_token, post_id)

        time.sleep(0.5)

    print(f"Post {post_id} commented {N} times")

# Like a post using API feed/post/:post_id/like | Needs auth_token & Post Id
def like_post(auth_token, post_id):
    like_url = base_url + f"/feed/post/{post_id}/like"
    headers = {"Authorization": auth_token}
    like_response = requests.put(like_url, headers=headers)

    if like_response.status_code != 200:
        print(f"Failed to like post: {like_response.json()}")
    else:
        print(f"Post {post_id} liked | {like_response.json()}")

# Comment on a post using API feed/post/:post_id/comment | Needs auth_token & Post Id
def comment_post(auth_token, post_id):
    comment_url = base_url + f"/feed/post/{post_id}/comment"
    headers = {"Authorization": auth_token}
    comment_response = requests.post(comment_url, json={"text": "Some Comment"}, headers=headers)

    if comment_response.status_code != 200:
        print(f"Failed to comment on post: {comment_response.json()}")
    else:
        print(f"Post {post_id} commented | {comment_response.json()}")


# Update N and postId as per requirement
like_N_times(1000, post_ids[0])
comment_N_times(1000, post_ids[1])
like_N_times(100, post_ids[2])
comment_N_times(100, post_ids[3])