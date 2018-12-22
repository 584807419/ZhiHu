#coding:utf-8
from flask import Flask, render_template, Blueprint
from config import config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from flask_pagedown import PageDown
import flask_whooshalchemyplus
from flask_cache import Cache

#构造文件导入了大多数正在使用的 Flask 扩展。由于尚未初始化所需的程序实例，所以没有初始化扩展，创建扩展类时没有向构造函数传入参数。
mail = Mail()
monment = Moment()
pagedown = PageDown()

login_manager = LoginManager()
#LoginManager 对象的 session_protection 属性可以设为 None 、 'basic' 或 'strong' ，以提供不同的安全等级防止用户会话遭篡改。设为 'strong' 时，Flask-Login 会记录客户端 IP地址和浏览器的用户代理信息，如果发现异动就登出用户。
login_manager.session_protection = 'strong'
#login_view 属性设置登录页面的端点。登录路由在蓝本auth中定义，因此要在前面加上蓝本的名字auth。
login_manager.login_view = 'auth.login'

db = SQLAlchemy()
#缓存
cache = Cache()

#create_app() 函数就是程序的工厂函数，接受一个参数，是程序使用的配置名
def create_app(config_name):
    app = Flask(__name__)

    #配置类在 config.py 文件中定义，其中保存的配置可以使用 Flask  app.config 配置对象提供的 from_object() 方法直接导入程序
    app.config.from_object(config[config_name])

    config[config_name].init_app(app)

    #蓝本在工厂函数 create_app() 中注册到程序上
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/api/v1.0')

    #程序创建并配置好后，就能初始化扩展了。在之前创建的扩展对象上调用 init_app() 可以完成初始化过程。
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    monment.init_app(app)
    pagedown.init_app(app)

    flask_whooshalchemyplus.init_app(app)

    cache.init_app(app)

    #工厂函数返回创建的程序示例
    return app
