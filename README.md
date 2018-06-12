# webIO
Websocket based API framework based on JSON

This is basd on the Sanic HTTP framework where you can define endpoints via a function.



### Warning:
This is a dev build of an idea I had. Nothing is final.

### Examples:
```py
import webIO
import asyncio
import pymongo
import os

server = webIO.Server(name='WebIO Example Server', port=1423)

server.config['base_action_name'] = 'webio' # for setting the action field as "webio"
# example: {"action": "webio.{endpoint_name}", "thing_1": True}

# add the database to the script wide context
database_connection = pymongo.MongoClient(os.getenv('mongo_db'))

class User():
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@server.hook('before_request')
async def before_request(request):
    """
    This hooks adds the database connection into
    the request object
    """
    db = database_connection.database
    user = None
    if 'authentication' in request:
        # check if key in request
        user_data = db.users.find_one({'session_token':request['authentication'] })
        request.session['user'] = User(**user_data)
    # extends the request object to have the returned 
    # attributes
    return {'user': user,
            'db': db}


@server.endpoint('test', requires=['username'])
async def test(request):
    return {'msg': f'hello, {username}'}

@server.endpoint('kill_server')
async def kill_server(request):
    print(request.session)
    try:
        request.session['test'].append(random.randint(0,14500000))
    except:
        request.session['test'] = [random.randint(0,14500000)]
    
    return


print('Starting server')
server.serve() #  not a coro but freezes everything until its done
```
