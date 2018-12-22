# coding:utf-8
# !/usr/bin/env python

import sys
import os
from app import create_app, db
from app.models import User, Role, Permission, Post, Follow, Comment
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand
from flask_bootstrap import Bootstrap

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)
bootstrap = Bootstrap(app)

reload(sys)
sys.setdefaultencoding('utf8')

def make_shell_context():
    return dict(app=app, db=db, User=User, Follow=Follow, Role=Role,
                Permission=Permission, Post=Post, Comment=Comment)

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
