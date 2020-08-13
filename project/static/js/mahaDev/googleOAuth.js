function authServer(token, element){
    $.ajax({
        url: "/api/login",
        data: {"type": "google", "google_id_token": token},
        type: "POST",
        success: function(data){
            console.log("Google auth success", data);
            window.location.href = $(element).attr("data-next");
        },
        error: function(data){
            console.log("Google auth failure", data);
        }
    });
}
function attachSignin(element) {
    auth2.attachClickHandler(element, {},
        function(googleUser) {
            var profile = googleUser.getBasicProfile();
            var id_token = googleUser.getAuthResponse().id_token;
            document.getElementById('name').value = profile.getName();
            document.getElementById('email').value = profile.getEmail();
            document.getElementById('profile_pic').value = profile.getImageUrl();
            $('.profile-pic-wrapper .img-holder').css("background-image","url(" + profile.getImageUrl() + ")");
            console.log('ID: ' + profile.getId()); // Do not send to your backend! Use an ID token instead.
            console.log('Name: ' + profile.getName());
            console.log('Image URL: ' + profile.getImageUrl());
            console.log('Email: ' + profile.getEmail()); // This is null if the 'email' scope is not present.
            // authServer(id_token, element);
        }, function(error) {
            console.log(JSON.stringify(error, undefined, 2));
        });
}
(function(w,d,s){
    var f = d.getElementsByTagName(s)[0],
        j = d.createElement(s);
    j.async = true;
    j.defer = true;
    j.onload = function(){
        gapi.load('auth2', function(){
            // Retrieve the singleton for the GoogleAuth library and set up the client.
            auth2 = gapi.auth2.init({
                client_id: "{{ google_oauth_client_id }}",
                cookiepolicy: 'single_host_origin',
                // Request scopes in addition to 'profile' and 'email'
                // scope: 'additional_scope'
            });
            $(".googleSignin").removeClass("dN").each(function(){
                attachSignin(this);
            })
        });
    };
    j.onerror = function(){};
    j.src = 'https://apis.google.com/js/api:client.js';
    f.parentNode.insertBefore(j,f);
})(window,document,'script');