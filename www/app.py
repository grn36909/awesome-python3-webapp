#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
手动向数据库(awesome)中插入一列信息
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
