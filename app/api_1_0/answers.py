#coding:utf-8
from flask import jsonify, request, g, url_for, current_app, make_response
from .. import db
from ..models import Post, Permission, Answer
from . import api
from .decorators import permission_required


@api.route('/answers/')
def get_answers():
    page = request.args.get('page', 1, type=int)
    pagination = Answer.query.order_by(Answer.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_answers_PER_PAGE'],
        error_out=False)
    answers = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_answers', page=page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_answers', page=page+1, _external=True)
    return jsonify({
        'answers': [answer.to_json() for answer in answers],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/answers/<int:id>')
def get_answer(id):
    answer = Answer.query.get_or_404(id)
    return jsonify(answer.to_json())


@api.route('/posts/<int:id>/answers/')
def get_post_answers(id):
    post = Post.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = post.answers.order_by(Answer.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_ANSWERS_PER_PAGE'],
        error_out=False)
    answers = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_post_answers', id=id, page=page-1,
                       _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_post_answers', id=id, page=page+1,
                       _external=True)
    return jsonify({
        'answers': [answer.to_json() for answer in answers],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/posts/<int:id>/answers/', methods=['POST'])
@permission_required(Permission.COMMENT)
def new_post_answer(id):
    post = Post.query.get_or_404(id)
    answer = Answer.from_json(request.json)
    answer.author = g.current_user
    answer.post = post
    db.session.add(answer)
    db.session.commit()
    return jsonify(answer.to_json()), 201, \
        {'Location': url_for('api.get_answer', id=answer.id,
                             _external=True)}

#这个配合前端的_posts.html中的ajax getJSON 方法来得到赞同最高的答案的内容和赞同数并且显示出来
@api.route('/posts/<int:id>/ajax/answers/')
def get_ajax_post_answers(id):
    post = Post.query.get_or_404(id)
    answer = (Answer.query.filter_by(post_id=id).order_by(Answer.agreements_num.desc())).first()
    try:
        return jsonify({
            'answers_body': (answer.body)[:176],
            'answer_vote': answer.agreements_num
        })
    except:
        return make_response("404")
