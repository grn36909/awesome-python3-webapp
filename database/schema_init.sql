-- schema.sql

-- 与 MySQL 相同的名称必须添加 "`"符号

drop database if exists `awesome`;      -- 删除数据库
create database `awesome`;              -- 新建数据库
use `awesome`;                          -- 使用数据库

drop user 'www-data'@'localhost';       -- 删除用户
create user 'www-data'@'localhost' identified by 'www-data';    -- 新建用户及密钥

grant select, insert, update, delete on `awesome`.* to 'www-data'@'localhost';  -- 指定用户操作权利及登入方式

create table users (                    -- 建立表
    `id` varchar(50) not null,          -- 建立列
    `email` varchar(50) not null,
    `passwd` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_at` real not null,
    unique key `idx_email` (`email`),   -- 唯一索引
    key `idx_created_at` (`created_at`),-- 普通索引(index)
    primary key (`id`)                  -- 主键索引
) engine=innodb default charset=utf8;   -- engine=存储引擎(表类型) charset=字符集

create table blogs (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `name` varchar(50) not null,
    `summary` varchar(200) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table comments (
    `id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;