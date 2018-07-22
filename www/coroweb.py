#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
注释参考：https://github.com/Eliefly/python-web-blog/blob/master/www/coroweb.py
'''

import asyncio, os, inspect, logging, functools # inspect=检查事实对象, functools=可调用对象的高阶函数和操作

from urllib import parse                        # urllib=URL处理模块
from aiohttp import web                         # aiohttp=异步HTTP客户端/服务器

from apis import APIError                       # apis.py

# get 和 post 为修饰方法,主要是为对象上加上'__method__'和'__route__'属性
# 为了把我们定义的url实际处理方法，以get请求或post请求区分

# 把一个函数映射为一个URL处理函数
def get(path):
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

# 把一个函数映射为一个URL处理函数
def post(path):
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

# 如果url处理函数需要传入关键字参数，且默认是空得话，获取这个key
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

# 如果url处理函数需要传入关键字参数，获取这个key
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

# 如果url处理函数需要传入关键字参数，返回True。Example：api_blogs(*, page='1')为true
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

# 如果url处理函数的参数是**kw，返回True
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

# 如果url处理函数的参数是request，返回True
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

# 从URL函数中分析其需要接收的参数，
# 从request中获取必要的参数，调用URL函数，
# 然后把结果转换为web.Response对象
class RequestHandler(object):

    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)         # 下面的一系列是为了检测url处理函数的参数类型
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):
        kw = None                                           # 获取参数
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':                    # 如果是post请求，则读请求的body
                if not request.content_type:                # 如果request的头中没有content-type，则返回错误描述
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower()           # 字符串全部转为小写
                if ct.startswith('application/json'):       # 如果是'application/json'类型
                    params = await request.json()           # 把request的body，按json的方式输出为一个字典
                    if not isinstance(params, dict):        # 解读出错或params不是一个字典，则返回错误描述
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params                             # 保存这个params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):    # 如果是'application/x-www-form-urlencoded'，或'multipart/form-data'，直接读出来并保存
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':                     # 如果是get请求，则读请求url字符串
                qs = request.query_string                   # 看url有没有参数，即？后面的字符串
                if qs:                                      # 如果有的话，则把参数以键值的方式存起来赋值给kw
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:                                      # 如果kw为空得话，kw就直接获取match_info的参数值
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:    # 如果kw有值得话(已经从GET或POST传进来了参数值)
                # remove all unamed kw:
                copy = dict()
                for name in self._named_kw_args:            # 从kw中筛选出url处理方法需要传入的参数对
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in request.match_info.items():         # 处理完从GET或POST传进来了参数值, 再把获取match_info的参数值添加到kw中。
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:                           # 如果参数需要传'request'参数，则把request实例传入
            kw['request'] = request
        # check required kw:
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)                      # 对url进行处理
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

# 添加静态页面的路径
def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

# 注册一个URL处理函数
def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:                      # 获取'__method__'和'__route__'属性，如果有空则抛出异常
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn): # 判断fn是不是协程(即@asyncio.coroutine修饰的) 并且 判断是不是fn 是不是一个生成器(generator function)
        fn = asyncio.coroutine(fn)                          # 都不是的话，强行修饰为协程
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

# 自动搜索传入的module_name的module的处理函数
def add_routes(app, module_name):
    n = module_name.rfind('.')                              # 检查传入的module_name是否有'.'
    if n == (-1):                                           # 没有'.',则传入的是module名
        mod = __import__(module_name, globals(), locals())
    else:
        # name = module_name[n+1:]
        # mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
        mod = __import__(module_name[:n], globals(), locals())
    for attr in dir(mod):                                   # 遍历mod的方法和属性,主要是注册URL处理函数
        if attr.startswith('_'):                            # 如果是以'_'开头的，一律pass，我们定义的处理方法不是以'_'开头的
            continue
        fn = getattr(mod, attr)                             # 获取到非'_'开头的属性或方法
        if callable(fn):                                    # 取能调用的，说明是方法
            method = getattr(fn, '__method__', None)        # 检测'__method__'和'__route__'属性
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)                          # 如果都有，说明使我们定义的处理方法，加到app对象里处理route中
