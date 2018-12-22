# coding:utf-8
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from wtforms import ValidationError
from ..models import User, Role
from flask_pagedown.fields import PageDownField


# 提问题表单
class AskQuestionForm(FlaskForm):
    """
    # 可以将ite-packages\flask_bootstrap\templates\bootstrap\wtf.html第56行改为{{field}},不再让他使用默认得按钮样式
    """
    title = StringField('问题标题', validators=[DataRequired()])
    body = PageDownField('问题描述（可选）：')
    img = FileField('图片')
    submit = SubmitField('提问', render_kw={'class': 'btn btn-primary'})



# 文章内容表单
class PostForm(FlaskForm):
    body = PageDownField('提出你感兴趣的问题', validators=[DataRequired()])
    submit = SubmitField('提问')


# 个人信息编辑表单
class EditProfileForm(FlaskForm):
    name = StringField('名字', validators=[Length(0, 64)])
    location = StringField('位置', validators=[Length(0, 64)])
    about_me = TextAreaField('简介')
    submit = SubmitField('确定修改')


# WTForms 对 HTML 表单控件 <select> 进行 SelectField 包装，从而实现下拉列表，用来在这个表单中选择用户角色。 SelectField 实例必须在其 choices 属性中设置各选项。选项必须是一个由元组组成的列表，各元组都包含两个元素：选项的标识符和显示在控件中的文本字符串。 choices 列表在表单的构造函数中设定，其值从 Role 模型中获取，使用一个查询按照角色名的字母顺序排列所有角色。元组中的标识符是角色的 id ，因为这是个整数，所以在 SelectField 构造函数中添加 coerce=int 参数，从而把字段的值转换为整数，而不使用默认的字符串。
# 管理员级#个人信息编辑表单
class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    # email 和 username 字段的构造方式和认证表单中的一样，但处理验证时需要更加小心。验证这两个字段时，首先要检查字段的值是否发生了变化，如果有变化，就要保证新值不和其他用户的相应字段值重复；如果字段值没有变化，则应该跳过验证。为了实现这个逻辑，表单构造函数接收用户对象作为参数，并将其保存在成员变量中，随后自定义的验证方法要使用这个用户对象。
    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


# 回答输入表单
class AnswerForm(FlaskForm):
    body = PageDownField(validators=[DataRequired()])
    submit = SubmitField('提交回答')


# 评论输入表单
class CommentForm(FlaskForm):
    body = StringField('说你所想', validators=[DataRequired()])
    submit = SubmitField('评论')
