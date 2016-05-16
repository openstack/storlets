=====================
StorletsDockerGateway
=====================

The StorletDockerGateway implements the StorletsGatewayBase API, which is called by the storlet middleware. The API is defined as follows:

    '''
    validates correctness of the storlet name as well as mandatory headers
    params:
    req  the Swift request
    '''
    def validateStorletUpload(req)

    '''
    Checks that access to the container / object is authorized
    params:
    req  the Swift request
    '''
    def authorizeStorletExecution(req)

    '''
    Checks that access to the container / object is authorized
    params:
    req  the Swift request
    '''
    def augmentStorletRequest(req)

    '''
    Invoke the PUT proxy implementation of the gateway
    params:
    req  the Swift request as received from client
    container the targeted container
    obj the targeted object
    '''
    def gatewayProxyPutFlow(req, container,obj)

    '''
    Checks that access to the container / object is authorized
    params:
    req  the Swift request
    container the targeted container
    obj the targeted object
    orig_resp this is the Swift response of the plain GET request applied to the targeted object (that is without Storlet invocation)
    '''
    def gatewayObjectGetFlow(req, container, obj, orig_resp)
