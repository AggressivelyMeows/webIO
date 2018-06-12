import websockets
import asyncio
import json

from .request import Request
from .blueprint import Blueprint

INIT_CONFIG = {'base_action_name':'base', # Changes the default action from `base` to whatever the user wants
               'test':1,
               'allow_map':False, # disable API map by default for securty reasons
               # this will allow people to see what endpoints are avalible from a certain blueprint
               # base.map -> {"test": {"requires": ["username", "password"]}}
               # dev features
               }

class Client():
    def __init__(self, id, websocket):
        self.id = 0

        self._websocket = websocket 

    def set(self, key, value):
        setattr(self, key, value)

    async def send(self, json_encoded_message):
        await self._websocket.send(json_encoded_message)


class Server():
    def __init__(self, name = 'WebI/O Server',
                 port = 8000,
                 config = INIT_CONFIG,
                 path='/',
                 loop = asyncio.get_event_loop()):
        self.name = name
        self.port = port
        self.config = config
        self.path = path

        self.clients = [] # dict to be populated with clients

        self.endpoints = {'base':{}} # dict for endpoint storage
        # see server.add_blueprint for more

        self.hooks = {} # for the hooks in the server
        # basicly acting as middleware
        # you can view the hooks by calling server.hooks
        # the server will run them in the order they were defined
        # so you need to be careful if you are editing the 
        # request data 

        self.loop = loop

    def add_endpoint(self, name, function):
        """
        Manually adds an endpoint to the server
        """
        try:
            self.endpoints[self.config['base_action_name']][name] = function
        except:
            self.endpoints[self.config['base_action_name']] = {name: function}
            

    async def _request_error(self, error_json):
        # the endpoint must always return a coro, 
        # so we just make one and wrap
        # the error code into this
        # nice and neat coroutine!
        return {'error':error_json,
                'code':10103}

    def endpoint(self, name, requires=[], error_msg=''):
        """
        Same as blueprint.py except sets
        the API name as `base`
        This allows for direct use of the framework
        without needing a blueprint
        """
        def _endpoint(func):
            def wrapper(*args, **kwargs):
                
                kwargs = {}
                for req in requires:
                    requires_convert = False
                    if ':' in req:
                        # we have a converter to 
                        # deal with
                        requires_convert = True
                        before_convert = req.split(':')[0]
                    else:
                        before_convert = req

                    if before_convert in dict(args[0]):
                        # if the required var is in the request
                        # add it to the kwargs
                        # else, raise 10103 error
                        # (missing args)

                        # if the require has ":"
                        # we convert to the string after the ":"
                        # int or str for instance

                        if requires_convert:
                            req, converter = req.split(':')
                            if converter == 'int':
                                # convert to number
                                kwargs[req] = int(dict(args[0])[req])
                            elif converter == 'str':
                                kwargs[req] = str(dict(args[0])[req])

                            else:
                                raise TypeError('Invalid converter: must be "int" or "str"')
                        else:
                            kwargs[req] = dict(args[0])[req]

                    else:
                        if ':' in before_convert:
                            missing = before_convert.split(':')[0]
                        else:
                            missing = before_convert

                        return self._request_error(f'{missing.title()} is missing from request')
                        

                return func(args[0], **kwargs)

            self.add_endpoint(name=name,
                             function=wrapper)
            return wrapper

        return _endpoint

    def hook(self, hook_name):
        """
        Same as blueprint.py except sets
        the API name as `base`
        This allows for direct use of the framework
        without needing a blueprint
        """
        def _hook(func):
            def wrapper(*args, **kwargs):
                # add the hook to the server list

                return func(args[0], **kwargs)


            try:
                self.hooks[hook_name].append(wrapper)
            except KeyError:
                self.hooks[hook_name] = [wrapper]

            return wrapper
        return _hook

    def serve(self):
        """
        Start the server and listen on 
        self.port for clients
        """
        start_server = websockets.serve(self._websocket_consumer,
                                        '0.0.0.0',
                                        self.port)

        self.loop.run_until_complete(start_server)
        self.loop.run_forever()

    async def run_hooks(self, hook_name, *args, **kwargs):
        hooks = self.hooks.get(hook_name, [])
        if hooks:
            for hook in hooks:
                self.loop.create_task(hook(*arg, **kwargs))


    async def _websocket_consumer(self, websocket, path):

        await self.run_hooks('on_connection', websocket)

        # now we set up a session object
        # to keep allow for a persistant system

        session = {}

        while 1:
            try:
                message = await websocket.recv()
            except:
                pass

            
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                # failed to load, return error
                await websocket.send(json.dumps({'error': 'Could not decode JSON from request'}))
                continue 

            if 'action' not in message:
                # if action field is missing
                await websocket.send(json.dumps({'error': 'Action field missing from request'}))
                continue

            # so everything is good,
            # lets send it to the endpoint that it requested

            try:
                part_1, part_2 = message['action'].split('.')
            except:
                # malformed action field
                await websocket.send(json.dumps({'error': 'Action field is malformed. Please check docs for proper formatting'}))
                continue

            try:
                endpoint = self.endpoints[part_1.lower()][part_2.lower()]
            except:
                await websocket.send(json.dumps({'error': 'Endpoint was not found'}))
                continue

            request_data = message

            request_data['session'] = session

            try:
                hooks = self.hooks['before_request']
            except KeyError:
                pass
            else:
                for hook in hooks:
                    new_data = await hook(request_data)

                    for k, v in new_data.items():
                        request_data[k] = v
                    
            

            response = await endpoint(Request(**request_data))
            

            if response:
                if isinstance(response, dict):
                    if 'error' in response:
                        # there was an error
                        await websocket.send(json.dumps({'success': False,
                                                         'error':response['error'],
                                                         'code':response.get('code', 500)}))
                    else:
                        await websocket.send(json.dumps({'success': True,
                                                         'response': response,
                                                         'action': message['action']}))
