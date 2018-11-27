#coding:utf-8
#coding:utf-8
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,BooleanField,SubmitField
from wtforms.validators import DataRequired,Length,Email,EqualTo
from wtforms import ValidationError
from ..models import User

#继承Flask-WTF 的Form类来编写表单,电子邮件字段用到了 WTForms 提供的 Length() 和 Email() 验证函数。 PasswordField 类表示属性为 type="password" 的 <input> 元素。 BooleanField 类表示复选框。
#登录页面使用的模板保存在 auth/login.html 文件中。这个模板只需使用 Flask-Bootstrap 提供的 wtf.quick_form() 宏渲染表单即可
class LoginForm(FlaskForm):
    #可以在表单类里传入一个字典（render_kw），把需要添加到字段的属性以键值对的形式写进去,前端就能渲染出来
    email = StringField(u'邮箱账号', validators=[DataRequired(u'邮箱不能为空！'),Length(1,64),Email()],render_kw={'aria-label':u'邮箱', 'placeholder': u'邮箱'})
    password = PasswordField('密码',validators=[DataRequired()],render_kw={'aria-label':u'密码', 'placeholder': u'密码（不少于 6 位）','type':'password','autocomplete':'off'})
    remember_me = BooleanField('下次自动登录')
    submit = SubmitField(u'登录')

class RegisteationForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(),Length(1,64),Email()],render_kw={'aria-label':u'邮箱', 'placeholder': u'邮箱'})
    username = StringField('用户名',validators=[DataRequired(),Length(1.64)],render_kw={'aria-label':u'用户名', 'placeholder': u'昵称'})
    #安全起见，密码要输入两次。此时要验证两个密码字段中的值是否一致，这种验证可使用WTForms 提供的另一验证函数实现，即 EqualTo 。这个验证函数要附属到两个密码字段中的一个上，另一个字段则作为参数传入
    password = PasswordField('密码',validators=[DataRequired(),EqualTo('password2', message=u'两次输入的密码必须一致')],render_kw={'aria-label':u'密码', 'placeholder': u'密码','type':'password','autocomplete':'off'})
    password2 = PasswordField('确认密码',validators=[DataRequired()],render_kw={'aria-label':u'确认密码', 'placeholder': u'确认密码','type':'password','autocomplete':'off'})
    submit = SubmitField(u'确认注册')

    #如果表单类中定义了以validate_ 开头且后面跟着字段名的方法，这个方法就和常规的验证函数一起调用。本例分别为 email 和 username 字段定义了验证函数，确保填写的值在数据库中没出现过,自定义的验证函数要想表示验证失败，可以抛出 ValidationError 异常，其参数就是错误消息。
    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('此邮箱已经被注册过了')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('此昵称已经被注册过了')

#修改密码的表单
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField(u'旧密码',validators=[DataRequired()],render_kw={'aria-label':u'旧密码', 'placeholder': u'旧密码'})
    password = PasswordField(u'新密码',validators=[DataRequired(),EqualTo('password2',message=u'两次输入的密码必须一致')],render_kw={'aria-label':u'新密码', 'placeholder': u'新密码'})
    password2 = PasswordField(u'确认新密码',validators=[DataRequired()])
    submit = SubmitField(u'更改密码')

#发送重置密码请求输入邮箱的表单
class PasswordResetRequestForm(FlaskForm):
    email = StringField(u'邮箱地址',validators=[DataRequired(), Length(1,64),Email()])
    submit = SubmitField('发送重置邮件')

#重置密码输入新密码的表单
class PasswordResetForm(FlaskForm):
    email = StringField(u'邮箱地址',validators=[DataRequired(),Length(1,64),Email()])
    password = PasswordField(u'新的密码', validators=[DataRequired(),EqualTo('password2',message=u'两次输入的密码必须一致')])
    password2 = PasswordField(u'确认新密码',validators=[DataRequired()])
    submit = SubmitField(u'确认新的密码')

    def validate_email(self, field):
        if User.query.filtrt_by(email=field.data).first() is None:
            raise ValidationError(u'邮箱和注册邮箱不一致')

#修改邮箱地址的表单
class ChangeEmailForm(FlaskForm):
    email = StringField(u'新的邮箱',validators=[DataRequired(),Length(1,64),Email()])
    password = PasswordField(u'密码',validators=[DataRequired()])
    submit = SubmitField(u'确认新的邮箱')

    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError(u'邮箱已经存在,请重试')
