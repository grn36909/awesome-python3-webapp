#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
参考资料：

1.廖老师python教程实战Day5-编写web框架理解
https://blog.csdn.net/eye_water/article/details/78822727

2.python 编写web框架中的url处理函数以及个人理解
https://blog.csdn.net/qq_38209122/article/details/79218326

3.Python中Web框架编写学习心得
https://www.jianshu.com/p/0fded26001e3
'''




'''
编写Web框架
'''
'''
import asyncio
import orm
from models import User, Blog, Comment



async def test(loop):
    # 创建连接池,里面的host,port,user,password需要替换为自己数据库的信息
    await orm.create_pool(loop=loop, port=3306, user='www-data', password='www-data', db='awesome')
    # 没有设置默认值的一个都不能少
    u = User(name='Test', email='test@example.com', passwd='123456', image='about:blank', id='0001')

    await u.save()
    await orm.destory_pool()

loop = asyncio.get_event_loop()         # 获取EventLoop:
loop.run_until_complete(test(loop))     # 把协程丢到EventLoop中执行
loop.close()                            # 关闭EventLoop
'''

import logging; logging.basicConfig(level=logging.INFO)     # logging=日志

import asyncio, os, json, time                              # asyncio=异步IO, os=操作系统, json=JSON编解码
from datetime import datetime                               # datatime=基本时间和日期格式

from aiohttp import web                                     # aiohttp=异步HTTP客户端/服务器
from jinja2 import Environment, FileSystemLoader            # 全功能模板引擎

import orm
from coroweb import add_routes, add_static

# 初始化jinja2
def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options = dict(                                                     # 初始化模板配置，包括模板运行代码的开始结束标识符，变量的开始结束标识符等
        autoescape = kw.get('autoescape', True),                        # 是否转义设置为True，就是在渲染模板时自动把变量中的<>&等字符转换为&lt;&gt;&amp;
        block_start_string = kw.get('block_start_string', '{%'),        # 运行代码的开始标识符
        block_end_string = kw.get('block_end_string', '%}'),            # 运行代码的结束标识符
        variable_start_string = kw.get('variable_start_string', '{{'),  # 变量开始标识符
        variable_end_string = kw.get('variable_end_string', '}}'),      # 变量结束标识符
        auto_reload = kw.get('auto_reload', True)                       # Jinja2会在使用Template时检查模板文件的状态，如果模板有修改， 则重新加载模板。如果对性能要求较高，可以将此值设为False
    )
    path = kw.get('path', None)                                         # 从参数中获取path字段，即模板文件的位置
    if path is None:                                                    # 如果没有，则默认为当前文件目录下的 templates 目录
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
                                                                        # Environment是Jinja2中的一个核心类，它的实例用来保存配置、全局对象，以及从本地文件系统或其它位置加载模板。
    env = Environment(loader=FileSystemLoader(path), **options)         # 这里把要加载的模板和配置传给Environment，生成Environment实例
                                                                        # filters: 一个字典描述的filters过滤器集合, 如果非模板被加载的时候, 可以安全的添加filters或移除较早的.
    filters = kw.get('filters', None)                                   # 从参数取filter字段
    if filters is not None:                                             # 如果有传入的过滤器设置，则设置为env的过滤器集合
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env                                         # 给webapp设置模板

# 记录URL日志的logger
async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        # await asyncio.sleep(0.3)
        return (await handler(request))
    return logger

# 这个解析request参数的，不知为何没有使用到。
async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (await handler(request))
    return parse_data

# 响应处理
async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)                                      # 调用相应的handler处理request
        if isinstance(r, web.StreamResponse):                           # 如果响应结果为web.StreamResponse类，则直接把它作为响应返回
            return r
        if isinstance(r, bytes):                                        # 如果响应结果为字节流，则把字节流塞到response的body里，设置响应类型为流类型，返回
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):                                          # 如果响应结果为字符串
            if r.startswith('redirect:'):                               # 先判断是不是需要重定向，是的话直接用重定向的地址重定向
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))                 # 不是重定向的话，把字符串当做是html代码来处理
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):                                         # 如果响应结果为字典
            template = r.get('__template__')                            # 先查看一下有没有'__template__'为key的值
            if template is None:                                        # 如果没有，说明要返回json字符串，则把字典转换为json返回，对应的response类型设为json类型
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:                                                       # 如果有'__template__'为key的值，则说明要套用jinja2的模板，'__template__'Key对应的为模板网页所在位置
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp                                             # 以html的形式返回
        if isinstance(r, int) and r >= 100 and r < 600:                 # 如果响应结果为int
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:                        # 如果响应结果为tuple且数量为2
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:             # 如果tuple的第一个元素是int类型且在100到600之间，这里应该是认定为t为http状态码，m为错误描述。或者是服务端自己定义的错误码+描述
                return web.Response(t, str(m))
        # default: 默认直接以字符串输出
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

# 初始化
async def init(loop):
    await orm.create_pool(loop=loop, port=3306, user='www-data', password='www-data', db='awesome') # 创建数据库连接池
    app = web.Application(loop=loop, middlewares=[
        logger_factory, response_factory
    ])
    init_jinja2(app, filters=dict(datetime=datetime_filter))            # 初始化jinja2模板
    add_routes(app, 'handlers')                                         # 添加请求的handlers，即各请求相对应的处理函数,参数'handlers'为模块名。
    add_static(app)                                                     # 添加静态文件所在地址
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)   # 启动
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

# 入口，固定写法
# 获取eventloop然后加入运行事件
loop = asyncio.get_event_loop()                                         # 获取EventLoop:
loop.run_until_complete(init(loop))                                     # 把协程丢到EventLoop中执行
loop.close()                                                            # 关闭EventLoop
