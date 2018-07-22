#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
编写Web App骨架
'''

import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

# 制作响应函数
async def index(request):
    text = '<h1>Awesome!</h1>'
    return web.Response(body=text.encode('utf-8'), content_type='text/html')

# Web app 服务器初始化
async def init(loop):
    app = web.Application(loop=loop)                                        # 制作响应函数集合
    app.router.add_route('GET', '/', index)                                 # 把响应函数添加到响应函数集合
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)   # 创建服务器(连接网址、端口，绑定handler)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()                                             # 创建事件
loop.run_until_complete(init(loop))                                         # 运行
loop.run_forever()                                                          # 服务器不关闭
