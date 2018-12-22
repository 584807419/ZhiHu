# coding:utf-8
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, url_for, request
from datetime import datetime
from markdown import markdown
import bleach, hashlib
from app.exceptions import ValidationError
from jieba.analyse.analyzer import ChineseAnalyzer


# 权限常量
class Permission:
    # 用十六进制来表示
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_ANSWERS = 0x08
    ADMINISTER = 0x80


# 角色
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role')

    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)

    # 在数据库中创建三个角色
    @staticmethod
    def insert_roles():
        # | 是按位或运算符：只要对应的二个二进位有一个为1时，结果位就为1。
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_ANSWERS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


# 关注人的关系表
class Follow(db.Model):
    __tablename__ = 'flowes'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# 赞同关系表,回答ID,用户ID
class Agreement(db.Model):
    __tablename__ = 'agreements'
    answer_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                          primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('answers.id'),
                        primary_key=True)


# Flask-Login 提供了一个 UserMixin 类其中包含这些is_authenticated()is_active() is_anonymous()get_id()方法的默认实现,咱们的用户类继承了它,就不用从模型中自己重新实现这些验证方法啦
# 用户
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    password_hash = db.Column(db.String(128))

    confirmed = db.Column(db.Boolean, default=False)

    posts = db.relationship('Post', backref='author', lazy='dynamic')

    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)

    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan'
                               )
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    answers = db.relationship('Answer', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    avatar_hash = db.Column(db.String(32))

    user = db.relationship('Agreement', backref='user', lazy='dynamic')

    # user = db.relationship('Agreement',
    #                        foreign_keys=[Agreement.user_id],
    #                        backref=db.backref('Agreement',backref='answer', lazy='joined'),
    #                        lazy='dynamic',
    #                        cascade='all, delete-orphan'
    #                        )

    # 关注的方法,视图函数中调用的
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    # 点赞的方法
    def agree(self, answer):
        print(answer.agreements_num)
        # if not self.is_agreeing(answer):
        f = Agreement(user_id=self.id, answer_id=answer.id)
        answer.agreements_num = answer.agreements_num + 1
        db.session.add(f)
        db.session.add(answer)

    def unagree(self, answer):
        f = Agreement.query.filter_by(user_id=self.id).filter_by(answer_id=answer.id).first()
        answer.agreements_num = answer.agreements_num - 1
        db.session.delete(f)
        db.session.add(answer)

    def is_agreeing(self, answer):
        return Agreement.query.filter_by(user_id=self.id).filter_by(answer_id=answer.id).first() is not None

    # followed_posts() 方法定义为属性，因此调用时无需加 ()
    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id) \
            .filter(Follow.follower_id == self.id)

    # 注意，为了保护隐私，这个方法中用户的某些属性没有加入响应，例如 email 和 role 。这段代码再次说明，提供给客户端的资源表示没必要和数据库模型的内部表示完全一致。
    # 把用户转换成 JSON 格式的序列化字典
    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
            'comments': url_for('api.get_post_comments', id=self.id,
                                _external=True),
            'comment_count': self.comments.count()
        }
        return json_post

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    # 定义默认的用户角色
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()

    # 定义获取头像的方法
    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(url=url, hash=hash, size=size, default=default,
                                                                     rating=rating)

    # 检查角色是否有指定的权限的方法
    def can(self, permissions):
        return self.role is not None and \
               (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmtion_token(self, expiration=3600):
        """
        itsdangerous 提供了多种生成令牌的方法。其中， TimedJSONWebSignatureSerializer 类生成具有过期
        时间的 JSON Web 签名（JSON Web Signatures，JWS).这个类的构造函数接收的参数是一个密钥，在 Flask 程序中可使用 SECRET_KEY 设置。
        dumps() 方法为指定的数据生成一个加密签名，然后再对数据和签名进行序列化，生成令牌字符串
        :param expiration:
        :return:
        """
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            # 解码令牌，序列化对象提供了 loads() 方法，其唯一的参数是令牌字符串。这个方法会检验签名和过期时间，如果通过，返回原始数据。如果提供给 loads() 方法的令牌不正确或过期了，则抛出异常
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    # 修改邮箱地址
    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(self.email.encode('coding:utf-8'))
        db.session.add(self)
        return True

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


# Flask-Login 要求程序实现一个回调函数load_user，使用指定的标识符加载用户.load_user接收以 Unicode 字符串形式表示的用户标识符。如果能找到用户，这个函数必须返回用户对象；否则返回 None
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 文章内容模型
class Post(db.Model):
    __tablename__ = 'posts'
    __searchable__ = ['title', 'body']
    __analyzer__ = ChineseAnalyzer()

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body_html = db.Column(db.Text)
    answers = db.relationship('Answer', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    # 把文章转换成 JSON 格式的序列化字典
    # url 、 author 和 comments 字段要分别返回各自资源的 URL，因此它们使用 url_for() 生成，所调用的路由即将在 API 蓝本中定义。注意，所有 url_for() 方法都指定了参数 _external=True ，这么做是为了生成完整的 URL，而不是生成传统 Web 程序中经常使用的相对 URL。这段代码还说明表示资源时可以使用虚构的属性。 comment_count 字段是博客文章的评论数量，并不是模型的真实属性，它之所以包含在这个资源中是为了便于客户端使用。
    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id, _external=True),
            'answers': url_for('api.get_post_answers', id=self.id, _external=True),
            'comment_count': self.answers.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)

    # 真正的转换过程分三步完成。首先， markdown()函数初步把Markdown文本转换成
    # HTML。然后，把得到的结果和允许使用的HTML标签列表传给clean()函数。 clean()
    # 函数删除所有不在白名单中的标签。转换的最后一步由linkify()函数完成，这个函数由
    # Bleach提供，把纯文本中的URL转换成适当的 < a > 链接。最后一步是很有必要的，因为
    # Markdown规范没有为自动生成链接提供官方支持。PageDown以扩展的形式实现了这个功能，因此
    # 在服务器上要调用linkify()函数
    @staticmethod
    def on_change_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(
            bleach.clean(markdown(value, output_format='html'), tags=allowed_tags, strip=True))

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                     title=forgery_py.lorem_ipsum.sentences(randint(1, 5)), timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()


db.event.listen(Post.body, 'set', Post.on_change_body)


class Answer(db.Model):
    __tablename__ = 'answers'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    # cascade 参数配置在父对象上执行的操作对相关对象的影响。比如，层叠选项可设定为：将用户添加到数据库会话后，要自动把所有关系的对象都添加到会话中。层叠选项的默认值能满足大多数情况的需求，但对这个多对多关系来说却不合用。删除对象时，默认的层叠行为是把对象联接的所有相关对象的外键设为空值。但在关联表中，删除记录后正确的行为应该是把指向该记录的实体也删除，因为这样能有效销毁联接。这就是层叠选项值delete-orphan 的作用。
    comments = db.relationship('Comment', backref='answer', lazy='dynamic', cascade='all, delete-orphan')

    answer = db.relationship('Agreement', backref='answer', lazy='dynamic')
    agreements_num = db.Column(db.Integer, default=0)

    # answer = db.relationship('Agreement',
    #                        foreign_keys=[Agreement.answer_id],
    #                        backref=db.backref('Agreement',backref='user', lazy='joined'),
    #                        lazy='dynamic',
    #                        cascade='all, delete-orphan'
    #                        )

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_answer = {
            'url': url_for('api.get_answer', id=self.id, _external=True),
            'post': url_for('api.get_post', id=self.post_id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestramp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id, _external=True),
            'agreements_num': self.agreements_num
        }
        return json_answer


db.event.listen(Answer.body, 'set', Answer.on_changed_body)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'))
