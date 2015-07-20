class StorletStubBase():

    def __init__(self, storlet_conf, logger, app, version, account,
                 container, obj):
        self.logger = logger
        self.app = app
        self.version = version
        self.account = account
        self.container = container
        self.obj = obj
        self.storlet_conf = storlet_conf
        self.storlet_metadata = None
        self.storlet_timeout = int(self.storlet_conf['storlet_timeout'])

    def validateStorletUpload(self, req):
        self.logger.debug("Storlet request validated")
        return True

    def authorizeStorletExecution(self, req):
        self.logger.debug("Storlet execution is authorized")
        return True

    def augmentStorletRequest(self, req):
        self.logger.debug("Storlet request augmeneted")

    def gatewayProxyPutFlow(self, sreq, container, obj):
        raise NotImplementedError("Not implemented gatewayProxyPutFlow")

    def gatewayProxyGETFlow(self, req, container, obj, orig_resp):
        raise NotImplementedError("Not implemented gatewayProxyGETFlow")

    def gatewayObjectGetFlow(self, req, sreq, container, obj):
        raise NotImplementedError("Not implemented gatewayObjectGetFlow")
