var updateBtns = document.getElementsByClassName('update-cart')

for(var i=0; i< updateBtns.length; i++){
    updateBtns[i].addEventListener('click',function(){
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('productId:',productId,'action:',action)
        console.log('USER:',user)

        updateUserOrder(productId, action)


    })

}

function updateUserOrder(productId, action){
    console.log('User is logged in, sending data...1era función......' )



    var url = '/solicitudes/update_item/'

    fetch( url, {
        method:'POST',
        headers:{
            'Content-Type':'application/json',
            'X-CSRFToken': csrftoken,
        },
        body:JSON.stringify({'productId':productId, 'action':action})
    })
    .then((response)=>{
        return response.json()
    })

    .then((data)=>{
        console.log('data:', data)
        location.reload()
    })
}


var BotonActualizar = document.getElementsByClassName('actualizar-carro')

for(var i=0; i< BotonActualizar.length; i++){
    BotonActualizar[i].addEventListener('click',function(){
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('productId:',productId,'action:',action)
        console.log('USER:',user)

        update_User_Order_Res(productId, action)


    })

}

function update_User_Order_Res(productId, action){
    console.log('User is logged in, sending data...2da función......' )



    var url = '/solicitudes/update_item_res/'

    fetch( url, {
        method:'POST',
        headers:{
            'Content-Type':'application/json',
            'X-CSRFToken': csrftoken,
        },
        body:JSON.stringify({'productId':productId, 'action':action})
    })
    .then((response)=>{
        return response.json()
    })

    .then((data)=>{
        console.log('data:', data)
        location.reload()
    })
}
