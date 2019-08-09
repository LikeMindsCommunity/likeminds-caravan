$(document).ready(function(){


    //pending list page
    $('#close_no_pending').click(function(){
        $('#no_pending').css("display","none");
    })

    $('.view_response').click(function(e){

       try{

          community_id=community


       }catch(e){

             $('.test').modal('show')
             return;

       }
       member_id=this.id
       send_data(member_id,community_id)

    function send_data(member_id,community_id){

    //function to send the ajax request to get the questions
   if(!is_promoter){
        $('#negative').css("display","block");
        $('#close_negative').click(function(){
            $('#negative').css("display","none");
        })
        return;
    }
           data={
           'member_id':member_id,
           'community_id':community_id
           }
           $.ajax({

            url:'/questions_responses',
            data:data,
            dataType:'json',
            success:function(data){

            var responses=data['response_list'];
            str="<div class='description'>"
            if(responses.length == 0)
            {
             str+="<div class='ui header'>"+"No questions found to join this community" + "</div>"
             str+="<div>"
            }else{

                for(var i=0;i<responses.length;i++)
                {
                    str+="<div class='ui header'>"+responses[i]['question'] + "</div>"
                    str+="<p>"+responses[i]['answer']+"</p>"
                }
               str=str+"<div>"
           }
           var html=` <div class="ui modal" id="checking">
                        <i class="close icon"></i>
                        <div class="header">
                            Response
                        </div>
                        <div class="image content">
                            <div class="ui medium image">
                                <img src="${data['image_url']}">
                            </div>

                            ${str}

                        <div class="actions">
                            <div class="ui black deny button decline" id="${member_id}">
                                Decline
                            </div>
                            <div class="ui positive right labeled icon button approve" id="${member_id}" >
                                Approve
                                <i class="checkmark icon"></i>
                            </div>
                        </div>
                    </div>`


           $('#set').html(html);
            $('#checking').modal('show');
           $('#set').html('');
            }
         })

}

//approve members
$(document).on('click', '.approve', function(){

member_id=this.id;
data={accepted:true,community_id:community_id+"",member_id:member_id}
 $.ajax({

            url:'/api/join',
            data:JSON.stringify(data),
            type: 'POST',
            dataType:'json',
            success:function(data){
                  console.log(data)
                  location.reload(true)

            }
         })

})

//decline members
$(document).on('click', '.decline', function(){

member_id=this.id;
data={accepted:false,community_id:community_id+"",member_id:member_id}
 $.ajax({

            url:'/api/join',
            data:JSON.stringify(data),
            type: 'POST',
            dataType:'json',
            success:function(data){
                  console.log(data)
                  location.reload(true)

            }
         })

})



})




})
