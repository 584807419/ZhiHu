#coding:utf-8
from flask import Blueprint

api = Blueprint('api', __name__)

#得把视图函数都注册到这个蓝本进去,要不然url_for()找不到的
from . import authentication, posts, errors, answers, decorators, posts, users
