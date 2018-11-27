#coding:utf-8
from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth
from ..models import User, AnonymousUser
from . import api
from .errors import unauthorized, forbidden

auth = HTTPBasicAuth()

#第一个认证参数可以是电子邮件地址或认证令牌。如果这个参数为空，那就和之前一样，假定是匿名用户。如果密码为空，那就假定 email_or_token 参数提供的是令牌，按照令牌的方式进行认证。如果两个参数都不为空，假定使用常规的邮件地址和密码进行认证。在这种实现方式中，基于令牌的认证是可选的，由客户端决定是否使用。为了让视图函数能区分这两种认证方法，我们添加了 g.token_used 变量。
@auth.verify_password
def verify_password(email_or_token, password):
    if email_or_token == '':
        g.current_user = AnonymousUser()
        return True
    if password == '':
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and \
            not g.current_user.confirmed:
        return forbidden('Unconfirmed account')


#由于这个路由也在蓝本中，所以添加到 before_request 处理程序上的认证机制也会用在这个路由上。为了避免客户端使用旧令牌申请新令牌，要在视图函数中检查 g.token_used 变量的值，如果使用令牌进行认证就拒绝请求。这个视图函数返回 JSON 格式的响应，其中包含了过期时间为 1 小时的令牌。JSON 格式的响应也包含过期时间。
@api.route('/token')
def get_token():
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token': g.current_user.generate_auth_token(
        expiration=3600), 'expiration': 3600})
