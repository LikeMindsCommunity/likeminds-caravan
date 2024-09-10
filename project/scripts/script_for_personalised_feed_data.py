import requests, time

base_url = "https://auth.likeminds.community"

api_key = "" # Add your API Key here
uuid_prefix = "sdk-user-" # sdk/initiate user unique id & name


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
