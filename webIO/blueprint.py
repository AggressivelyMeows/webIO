class Blueprint():
    def __init__(self, name):
        self.name = name
        self.coros = []

        self.db = server.db
        self.server = server

    async def error(self, error_json):
        # the endpoint must always return a coro, 
        # so we just make one and wrap
        # the error code into this
        # nice and neat coroutine!
        return {'error':error_json,
                'code':10103}

    def endpoint(self, name, requires=[], error_msg=''):
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

                        return self.error(f'{missing.title()} is missing from request')

                return func(args[0], **kwargs)


            self.coros.append({'name':name, 
                               'func':wrapper})
            return wrapper

        return _endpoint

    def require_auth(self, request):
        # ok so we need to get the user object first
        # this is a slight hack
        # we have no way of knowing if the server will
        # be run from __main__
        # but for now, we hope.
        user = server.verify_session(request.authentication)
        if user: 
            return True
        else:
            return False
