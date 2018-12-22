# coding:utf-8
from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from ..models import User
from .forms import LoginForm, RegisteationForm, ChangePasswordForm, PasswordResetForm, PasswordResetRequestForm, \
    ChangeEmailForm
from .. import db
from ..email import send_email


# before_request 钩子只能应用到属于蓝本的请求上。若想在蓝本中使用针对程序全局请求的钩子，必须使用 before_app_request 修饰器
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint \
                and request.endpoint[:5] != 'auth.' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


# 用户登录
# 提交登陆表单LoginForm后，如果数据能被所有验证函数接受，那么 validate_on_submit() 方法的返回值为 True 并执行登陆login_user，否则返回 False,让用户重试
@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            flash('登录成功!')
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('用户名或者密码错误,请重试!')
    # return render_template('auth/login.html',form=form)使用{{ wtf.quick_form(form) }}渲染表单方式登陆,先留着备用
    return render_template('auth/login1.html', form=form)  # 改用知乎样式,并且使用手写form表单的形式登陆


# 用户退出登录
# Flask-Login 提供了一个 login_required 修饰器,如果未认证的用户访问这个路由，Flask-Login 会拦截请求，把用户发往登录页面。
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已经退出登录')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """
    新用户注册
    注意，即便通过配置，程序已经可以在请求末尾自动提交数据库变化，这里也要添加db.session.commit() 调用。
    问题在于，提交数据库之后才能赋予新用户 id 值，而确认令牌需要用到 id ，所以不能延后提交
    :return:
    """
    form = RegisteationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmtion_token()
        login_user(user)
        send_email(user.email, u'请确认您的账户邮箱', 'auth/email/confirm', user=user, token=token)
        flash(u'注册成功,一封确认邮件已经发送到您的邮箱')
        return redirect(url_for('main.index'))
    return render_template('auth/register1.html', form=form)


# 重发激活邮件
@auth.route('/resend_confirmation')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmtion_token()
    # 第二个参数是指定templates里面的模版
    send_email(current_user.email, u'请确认您的账户邮箱', 'auth/email/confirm', user=current_user, token=token)
    flash('一封确认邮件已经发送到您的邮箱')
    return redirect(url_for('main.index'))


# 确认用户的账户
@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    # 除了检验令牌， confirm() 方法还检查令牌中的 id 是否和存储在 current_user 中的已登录用户匹配。如此一来，即使恶意用户知道如何生成签名令牌，也无法确认别人的账户。
    # 由于令牌确认完全在User 模型中完成，所以视图函数只需调用confirm()方法即可，然后 再根据确认结果显示不同的Flash消息。确认成功后，User模型中confirmed属性的值会被修改并添加到会话中，请求处理完后，这两个操作被提交到数据库。
    # 通过current_user这个User()类的一个实例来调用类中的方法非常的方便
    if current_user.confirmed:
        flash(u'您的账户已确认成功')
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash(u'您的账户已确认成功')
    else:
        flash(u'确认失败,请重新发送确认邮件再试')
    return redirect(url_for('main.index'))


# 修改密码
@auth.route('/change-passord', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash(u'密码已经更新')
            return redirect(url_for('main.index'))
        else:
            flash(u'密码无效')
    return render_template("auth/change_password.html", form=form)


# 重置密码的请求
@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, u'重置你的密码', 'auth/email/reset_passord', user=user, token=token,
                       next=request.args.get('next'))
        flash(u'一封重置密码邮件已经发给你了呦!')
    return render_template('auth/reset_password.html', form=form)


# 点了邮件中的链接后重置密码实际操作过程,验证token
@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validation_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash(u'密码更新成功')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)


# 发送修改电子邮件的地址的请求
@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, u'确认你的新邮箱地址', 'auth/email/change_email', user=current_user, token=token)
            flash(u'一封修改邮箱的确认邮件已经发给你了呦!')
            return redirect(url_for('main.index'))
        else:
            flash(u'无效的邮箱或者密码')
    return render_template("auth/change_email.html", form=form)


# 修改邮箱的实际操作过程
@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash(u'邮箱地址更新成功!')
    else:
        flash(u'邮箱地址更新失败!')
    return redirect(url_for('main.index'))
