# coding:utf-8

from flask import render_template, redirect, request, url_for, flash, abort, current_app, make_response
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User, Permission, Post, Role, Comment, Answer
from .forms import PostForm, EditProfileForm, EditProfileAdminForm, CommentForm, AskQuestionForm, AnswerForm
from .. import db, cache
from . import main
from ..decorators import admin_required, permission_required

import flask_whooshalchemyplus


@main.route('/', methods=['GET', 'POST'])
@cache.cached(timeout=5, key_prefix='index')
def index():
    """
    设置一个key_prefix来作为标记，然后，在内容更新的函数里面调用cache.delete('index')来删除缓存来保证用户访问到的内容是最新的

    新文章对象的 author 属性值为表达式 current_user._get_current_object() 。变量current_user 由 Flask-Login 提供，
    和所有上下文变量一样，也是通过线程内的代理对象实现。这个对象的表现类似用户对象，但实际上却是一个轻度包装，包含真正的用户对象。
    数据库需要真正的用户对象，因此要调用 _get_current_object() 方法。

    渲染的页数从请求的查询字符串（ request.args ）中获取如果没有明确指定则默认渲染第一页参数 type=int 保证参数无法转换成整数时，返回默认值。

    为了显示某页中的记录，要把 all() 换成 Flask-SQLAlchemy 提供的 paginate() 方法。页数是 paginate() 方法的第一个参数
    也是唯一必需的参数。可选参数 per_page 用来指定每页显示的记录数量；如果没有指定，则默认显示 20 个记录。另一个可选参数为 error_out
    当其设为 True 时（默认值），如果请求的页数超出了范围，则会返回 404 错误；如果设为 False ，页数超出范围时会返回一个空列表。
    为了能够很便利地配置每页显示的记录数量，参数 per_page 的值从程序的环境变量 FLASKY_POSTS_PER_PAGE 中读取。这样修改之后，
    首页中的文章列表只会显示有限数量的文章。若想查看第 2 页中的文章，要在浏览器地址栏中的 URL 后加上查询字符串 ?page=2。
    :return:
    """
    page = request.args.get('page', 1, type=int)
    show_followed = False
    query = Post.query
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
        if show_followed:
            query = current_user.followed_posts
    pagination = query.outerjoin(Post.answers).order_by(Post.timestamp.desc()).paginate(page,
                                                                                        per_page=current_app.config[
                                                                                            'FLASKY_POSTS_PER_PAGE'],
                                                                                        error_out=False)
    posts = pagination.items
    flask_whooshalchemyplus.index_one_model(Post)
    return render_template('index4.html', posts=posts, show_followed=show_followed, pagination=pagination)


@main.route('/askquestion', methods=['GET', 'POST'])
@login_required
def askquestion():
    """
    # 新文章对象的 author 属性值为表达式 current_user._get_current_object() 。
    # 变量current_user 由 Flask-Login 提供，和所有上下文变量一样，
    # 也是通过线程内的代理对象实现。这个对象的表现类似用户对象，
    # 但实际上却是一个轻度包装，包含真正的用户对象。数据库需要真正的用户对象，因此要调用 _get_current_object() 方法。

    # 渲染的页数从请求的查询字符串（ request.args ）中获取，如果没有明确指定，
    # 则默认渲染第一页。参数 type=int 保证参数无法转换成整数时，返回默认值。
    :return:
    """
    form = AskQuestionForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, body=form.body.data, author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for('.index'))

    page = request.args.get('page', 1, type=int)
    query = Post.query
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
        if show_followed:
            query = current_user.followed_posts

    # 为了显示某页中的记录，要把 all() 换成 Flask-SQLAlchemy 提供的 paginate() 方法。
    # 页数是 paginate() 方法的第一个参数，也是唯一必需的参数。可选参数 per_page 用来指定每页显示的记录数量；
    # 如果没有指定，则默认显示 20 个记录。另一个可选参数为 error_out ，当其设为 True 时（默认值），
    # 如果请求的页数超出了范围，则会返回 404 错误；如果设为 False ，页数超出范围时会返回一个空列表。
    # 为了能够很便利地配置每页显示的记录数量，参数 per_page 的值从程序的环境变量 FLASKY_POSTS_PER_PAGE 中读取。这
    # 样修改之后，首页中的文章列表只会显示有限数量的文章。若想查看第 2 页中的文章，要在浏览器地址栏中的 URL 后加上查询字符串 ?page=2。
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items

    # import flask_whooshalchemyplus
    # flask_whooshalchemyplus.index_one_model(Post)
    cache.delete('index')  # 删除缓存
    return render_template('askquestion.html', form=form, posts=posts, show_followed=show_followed,
                           pagination=pagination)


@main.route('/user/<id>')
def user(id):
    user = User.query.filter_by(id=id).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(page, per_page=current_app.config[
        'FLASKY_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts, pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.username
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    print(user.username)
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


# 编辑文章的路由
@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash('内容已经更新')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)


# 删除文章的路由
@main.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMINISTER):
        abort(403)
    db.session.delete(post)
    flash('问题已经删除')
    return redirect(url_for('.index'))


# 搜索文章的路由
@main.route('/search/', methods=['GET', 'POST'])
@login_required
def search():
    # 获取搜索表单传过来的数据
    keyword = request.form.get('q', 'default value')

    page = request.args.get('page', 1, type=int)
    show_followed = False

    # 为了显示某页中的记录，要把 all() 换成 Flask-SQLAlchemy 提供的 paginate() 方法。页数是 paginate() 方法的第一个参数，也是唯一必需的参数。可选参数 per_page 用来指定每页显示的记录数量；如果没有指定，则默认显示 20 个记录。另一个可选参数为 error_out ，当其设为 True 时（默认值），如果请求的页数超出了范围，则会返回 404 错误；如果设为 False ，页数超出范围时会返回一个空列表。为了能够很便利地配置每页显示的记录数量，参数 per_page 的值从程序的环境变量 FLASKY_POSTS_PER_PAGE 中读取。这样修改之后，首页中的文章列表只会显示有限数量的文章。若想查看第 2 页中的文章，要在浏览器地址栏中的 URL 后加上查询字符串 ?page=2。
    pagination = Post.query.whoosh_search(keyword).order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items

    return render_template('searched.html', posts=posts, show_followed=show_followed, pagination=pagination)


# 回答问题
@main.route('/post/<int:id>', methods=['GET', 'POST'])
@login_required
def post(id):
    cache.delete('view//')

    post = Post.query.get_or_404(id)
    form = AnswerForm()
    if form.validate_on_submit():
        answer = Answer(body=form.body.data,
                        post=post,
                        author=current_user._get_current_object()
                        )
        db.session.add(answer)
        flash('提交答案成功')
        # 评论按照时间戳顺序排列，新评论显示在列表的底部。提交评论后，请求结果是一个重定向，转回之前的 URL，但是在 url_for() 函数的参数中把 page 设为 -1 ，这是个特殊的页数，用来请求评论的最后一页，所以刚提交的评论才会出现在页面中。程序从查询字符串中获取页数，发现值为 -1 时，会计算评论的总量和总页数，得出真正要显示的页数。
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.answers.count() - 1) // \
               current_app.config['FLASKY_ANSWERS_PER_PAGE'] + 1
    pagination = post.answers.order_by(Answer.agreements_num.desc()).paginate(
        page, per_page=current_app.config['FLASKY_ANSWERS_PER_PAGE'], error_out=False
    )
    answers = pagination.items

    return render_template('post.html', posts=[post], form=form, answers=answers, pagination=pagination)


# 对答案进行评价
@main.route('/comment/<int:id>', methods=['GET', 'POST'])
@login_required
def comment(id):
    answer = Answer.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, answer=answer, author=current_user._get_current_object()
                          )
        db.session.add(comment)
        flash('评论成功')
        return redirect(url_for('main.comment', id=answer.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (answer.comments.count() - 1) // \
               current_app.config['FLASKY_ANSWERS_PER_PAGE'] + 1
    pagination = answer.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_ANSWERS_PER_PAGE'], error_out=False
    )
    comments = pagination.items

    return render_template('comment.html', answers=[answer], form=form, comments=comments, pagination=pagination)


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_ANSWERS)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Answer.query.order_by(Answer.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_ANSWERS_PER_PAGE'],
        error_out=False
    )
    answers = pagination.items
    return render_template('moderate.html', answers=answers, pagination=pagination, page=page)


# “关注”路由和视图函数
@main.route('/follow/<id>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(id):
    user = User.query.filter_by(id=id).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', id=id))
    current_user.follow(user)
    flash('You are now following %s.' % id)
    return redirect(url_for('.user', id=id))


# 取消关注
@main.route('/unfollow/<id>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(id):
    user = User.query.filter_by(id=id).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', id=id))
    current_user.unfollow(user)
    flash('You are not following %s anymore.' % id)
    return redirect(url_for('.user', id=id))


# “关注者”路由和视图函数
@main.route('/followers/<username>')
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed-by/<username>')
@login_required
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followed.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


# 点赞
@main.route('/agree/<id>')
@login_required
def agree(id):
    answer = Answer.query.filter_by(id=id).first()
    if answer is None:
        flash('答案找不到了')
        return redirect(url_for('.index'))
    if current_user.is_agreeing(answer):
        flash('已经点过赞了.')
        return redirect(url_for('.index'))
    current_user.agree(answer)
    flash('点赞成功')
    return redirect(url_for('.index'))


# 取消点赞
@main.route('/unagree/<id>')
@login_required
def unagree(id):
    answer = Answer.query.filter_by(id=id).first()
    if answer is None:
        flash('答案找不到了')
        return redirect(url_for('.index'))
    if not current_user.is_agreeing(answer):
        flash('还没点过赞呢.')
        return redirect(url_for('.index', id=id))
    current_user.unagree(answer)
    flash('取消成功!')
    return redirect(url_for('.index', id=id))


# 指向这两个路由的链接添加在首页模板中。点击这两个链接后会为 show_followed cookie 设定适当的值，然后重定向到首页。cookie 只能在响应对象中设置，因此这两个路由不能依赖 Flask，要使用 make_response()方法创建响应对象。
@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '')
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1')
    return resp


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_ANSWERS)
def moderate_enable(id):
    answer = Answer.query.get_or_404(id)
    answer.disabled = False
    db.session.add(answer)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_ANSWERS)
def moderate_disable(id):
    answer = Answer.query.get_or_404(id)
    answer.disabled = True
    db.session.add(answer)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))
